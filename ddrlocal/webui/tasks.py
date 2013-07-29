from datetime import datetime
import os
import shutil

from celery import task
from celery import Task
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

from django.contrib import messages

from ddrlocal.models.entity import DDRLocalEntity
from ddrlocal.models.file import DDRFile, hash

from DDR.commands import entity_annex_add


class DebugTask(Task):
    abstract = True
        
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        entity = args[2]
        entity.files_log(0,'DDRTask.ON_FAILURE')
    
    def on_success(self, retval, task_id, args, kwargs):
        entity = args[2]
        entity.files_log(1,'DDRTask.ON_SUCCESS')
    
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        entity = args[2]
        entity.files_log(1,'DDRTask.AFTER_RETURN')
        entity.files_log(1,'task_id: %s' % task_id)
        entity.files_log(1,'status: %s' % status)
        entity.files_log(1,'retval: %s' % retval)
        entity.files_log(1,'Unlocking %s' % entity.id)
        lockstatus = entity.unlock(task_id)
        if lockstatus == 'ok':
            entity.files_log(1,'unlocked')
        else:
            entity.files_log(0,lockstatus)
        entity.files_log(1, 'DONE\n')


@task(base=DebugTask, name='entity-add-file')
def entity_add_file( git_name, git_mail, entity, src_path, role, sort, label='' ):
    """
    @param entity: DDRLocalEntity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    """
    file_ = add_file(git_name, git_mail, entity, src_path, role, sort, label)
    return file_


def add_file( git_name, git_mail, entity, src_path, role, sort, label='' ):
    """Add file to entity
    
    This method breaks out of OOP and manipulates entity.json directly.
    Thus it needs to lock to prevent other edits while it does its thing.
    Writes a log to ${entity}/addfile.log, formatted in pseudo-TAP.
    This log is returned along with a DDRFile object.
    
    @param entity: DDRLocalEntity
    @param src_path: Absolute path to an uploadable file.
    @param role: Keyword of a file role.
    @param git_name: Username of git committer.
    @param git_mail: Email of git committer.
    @return file_ DDRFile object
    """
    f = None
                
    entity.files_log(1, 'ddrlocal.webui.tasks.add_file: START')
    entity.files_log(1, 'entity: %s' % entity.id)
    entity.files_log(1, 'src: %s' % src_path)
    entity.files_log(1, 'role: %s' % role)
    entity.files_log(1, 'sort: %s' % sort)
    entity.files_log(1, 'label: %s' % label)
    
    src_basename      = os.path.basename(src_path)
    src_exists        = os.path.exists(src_path)
    src_readable      = os.access(src_path, os.R_OK)
    if not os.path.exists(entity.files_path):
        os.mkdir(entity.files_path)
    dest_dir          = entity.files_path
    dest_dir_exists   = os.path.exists(dest_dir)
    dest_dir_writable = os.access(dest_dir, os.W_OK)
    dest_basename     = DDRFile.file_name(entity, src_path)
    dest_path         = os.path.join(dest_dir, dest_basename)
    dest_path_exists  = os.path.exists(dest_path)
    s = []
    if src_exists:         s.append('ok')
    else:                  entity.files_log(0, 'Source file does not exist: {}'.format(src_path))
    if src_readable:       s.append('ok')
    else:                  entity.files_log(0, 'Source file not readable: {}'.format(src_path))
    if dest_dir_exists:    s.append('ok')
    else:                  entity.files_log(0, 'Destination directory does not exist: {}'.format(dest_dir))
    if dest_dir_writable:  s.append('ok')
    else:                  entity.files_log(0, 'Destination directory not writable: {}'.format(dest_dir))
    #if not dest_path_exists: s.append('ok')
    #else:                  entity.files_log(0, 'Destination file already exists!: {}'.format(dest_path))
    preparations = ','.join(s)
    
    # do, or do not
    cp_successful = False
    if preparations == 'ok,ok,ok,ok':  # ,ok
        entity.files_log(1, 'Source file exists; is readable.  Destination dir exists, is writable.')
        
        f = DDRFile(entity=entity)
        f.role = role
        f.sort = sort
        f.label = label
        f.basename_orig = src_basename
        entity.files_log(1, 'Original filename: %s' % f.basename_orig)
        
        # task: get SHA1 checksum (links entity.filemeta entity.files records
        entity.files_log(1, 'Checksumming...')
        try:
            f.sha1   = hash(src_path, 'sha1')
            entity.files_log(1, 'sha1: %s' % f.sha1)
        except:
            entity.files_log(0, 'sha1 FAIL')
        try:
            f.md5    = hash(src_path, 'md5')
            entity.files_log(1, 'md5: %s' % f.md5)
        except:
            entity.files_log(0, 'md5 FAIL')
        try:
            f.sha256 = hash(src_path, 'sha256')
            entity.files_log(1, 'sha256: %s' % f.sha256)
        except:
            entity.files_log(0, 'sha256 FAIL')
        
        # task: extract_xmp
        entity.files_log(1, 'Extracting XMP data...')
        try:
            f.xmp = DDRFile.extract_xmp(src_path)
            if f.xmp:
                entity.files_log(1, 'got some XMP')
            else:
                entity.files_log(1, 'no XMP data')
        except:
            entity.files_log(0, 'XMP extract FAIL')
        
        # task: copy
        entity.files_log(1, 'Copying...')
        try:
            shutil.copy(src_path, dest_path)
        except:
            entity.files_log(0, 'copy FAIL')
        if os.path.exists(dest_path):
            cp_successful = True
            f.set_path(dest_path, entity=entity)
            entity.files_log(1, 'copied: %s' % f.path)
    
    thumbnail = None
    if f and cp_successful:
        # task: make thumbnail
        entity.files_log(1, 'Thumbnailing...')
        # NOTE: do this before entity_annex_add so don't have to lock/unlock
        try:
            thumbnail = f.make_thumbnail('500x500')
        except:
            log(lf, 0, 'thumbnail FAIL')
        if thumbnail:
            f.thumb = 1
        else:
            f.thumb = 0
        entity.files_log(1, 'f.thumb: %s' % f.thumb)
        if thumbnail and hasattr(thumbnail, 'name') and thumbnail.name:
            entity.files_log(1, 'thumbnail: %s' % thumbnail.name)
        
    if f and cp_successful:
        # TODO task: make access copy
        entity.files_log(1, 'TODO access copy')
    
    if f and cp_successful:
        entity.files_log(1, 'Adding %s to entity...' % f)
        entity.files.append(f)
        entity.files_log(1, 'entity.files: %s' % entity.files)
        entity.files_log(1, 'Writing %s' % entity.json_path)
        entity.dump_json()
        entity.files_log(1, 'done')
        try:
            entity.files_log(1, 'entity_annex_add(%s, %s, %s, %s, %s)' % (
                git_name, git_mail,
                entity.parent_path,
                entity.id, dest_basename))
            exit,status = entity_annex_add(
                git_name, git_mail,
                entity.parent_path,
                entity.id, dest_basename)
            entity.files_log(1, 'entity_annex_add: exit: %s' % exit)
            entity.files_log(1, 'entity_annex_add: status: %s' % status)
        except:
            entity.files_log(0, 'entity_annex_add: ERROR')
        
    entity.files_log(1, 'ddrlocal.webui.tasks.add_file: FINISHED')
    return f
