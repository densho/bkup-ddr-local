import os

from bs4 import BeautifulSoup

from django.conf import settings
from django.core.context_processors import csrf
from django.core.files import File
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import Http404, get_object_or_404, render_to_response
from django.template import RequestContext

from Kura import commands

# helpers --------------------------------------------------------------

def collection_entities(soup):
    """Given a BeautifulSoup-ified EAD doc, get list of entity UIDs
    
    <dsc>
      <head>
       Inventory
      </head>
      <c01>
       <did>
        <unittitle eid="ddr-testing-201304081359-1">
         Entity description goes here
        </unittitle>
       </did>
      </c01>
      <c01>
       <did>
        <unittitle eid="ddr-testing-201304081359-2">
         Entity description goes here
        </unittitle>
       </did>
      </c01>
     </dsc>
    """
    entities = []
    for tag in soup.find_all('unittitle'):
        e = tag['eid'].split('-')
        repo,org,cid,eid = e[0],e[1],e[2],e[3]
        entities.append( {'uid': tag['eid'],
                          'repo': repo,
                          'org': org,
                          'cid': cid,
                          'eid': eid,
                          'title': tag.string.strip(),} )
    return entities

def entity_files(soup, collection_abs, entity_rel):
    """Given a BeautifulSoup-ified METS doc, get list of entity files
    
    ...
    <fileSec>
     <fileGrp USE="master">
      <file CHECKSUM="fadfbcd8ceb71b9cfc765b9710db8c2c" CHECKSUMTYPE="md5">
       <Flocat href="files/6a00e55055.png"/>
      </file>
     </fileGrp>
     <fileGrp USE="master">
      <file CHECKSUM="42d55eb5ac104c86655b3382213deef1" CHECKSUMTYPE="md5">
       <Flocat href="files/20121205.jpg"/>
      </file>
     </fileGrp>
    </fileSec>
    ...
    """
    files = []
    for tag in soup.find_all('flocat'):
        cid = os.path.basename(collection_abs)
        f = {
            'abs': os.path.join(collection_abs, entity_rel, tag['href']),
            'name': os.path.join(cid, entity_rel, tag['href']),
            'size': 1234567,
        }
        files.append(f)
    return files


# views ----------------------------------------------------------------

def login( request ):
    return render_to_response(
        'webui/login.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )

def logout( request ):
    return render_to_response(
        'webui/logout.html',
        {},
        context_instance=RequestContext(request, processors=[])
    )

def collections( request ):
    collections = []
    colls = commands.collections_local(settings.DDR_BASE_PATH,
                                       settings.DDR_REPOSITORY,
                                       settings.DDR_ORGANIZATION)
    for coll in colls:
        if coll:
            coll = os.path.basename(coll)
            c = coll.split('-')
            repo,org,cid = c[0],c[1],c[2]
            collections.append( (coll,repo,org,cid) )
    return render_to_response(
        'webui/collections/index.html',
        {'repo': repo,
         'org': org,
         'collections': collections,},
        context_instance=RequestContext(request, processors=[])
    )

def collection( request, repo, org, cid ):
    collection_uid = '{}-{}-{}'.format(repo, org, cid)
    collection_path = os.path.join(settings.DDR_BASE_PATH, collection_uid)
    #
    exit,status = commands.status(collection_path)
    #exit,astatus = commands.annex_status(collection_path)
    #
    ead = open( os.path.join(collection_path, 'ead.xml'), 'r').read()
    ead_soup = BeautifulSoup(ead)
    #
    changelog = open( os.path.join(collection_path, 'changelog'), 'r').read()
    #
    entities = collection_entities(ead_soup)
    return render_to_response(
        'webui/collections/collection.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection_uid': collection_uid,
         'status': status,
         #'astatus': astatus,
         'ead': ead,
         'changelog': changelog,
         'entities': entities,},
        context_instance=RequestContext(request, processors=[])
    )

def collection_new( request, repo, org ):
    return render_to_response(
        'webui/collections/collection-new.html',
        {'repo': repo,
         'org': org,},
        context_instance=RequestContext(request, processors=[])
    )

def entity( request, repo, org, cid, eid ):
    collection_uid = '{}-{}-{}'.format(repo, org, cid)
    entity_uid     = '{}-{}-{}-{}'.format(repo, org, cid, eid)
    collection_abs = os.path.join(settings.DDR_BASE_PATH, collection_uid)
    entity_abs     = os.path.join(collection_abs,'files',entity_uid)
    entity_rel     = os.path.join('files',entity_uid)
    #
    mets = open( os.path.join(entity_abs, 'mets.xml'), 'r').read()
    mets_soup = BeautifulSoup(mets)
    #
    changelog = open( os.path.join(entity_abs, 'changelog'), 'r').read()
    #
    files = entity_files(mets_soup, collection_abs, entity_rel)
    return render_to_response(
        'webui/entities/entity.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'eid': eid,
         'collection_uid': collection_uid,
         'entity_uid': entity_uid,
         'collection_path': collection_abs,
         'entity_path': entity_abs,
         'mets': mets,
         'changelog': changelog,
         'files': files,},
        context_instance=RequestContext(request, processors=[])
    )

def entity_new( request, repo, org, cid ):
    collection_uid = '{}-{}-{}'.format(repo, org, cid)
    return render_to_response(
        'webui/entities/entity-new.html',
        {'repo': repo,
         'org': org,
         'cid': cid,
         'collection_uid': collection_uid,},
        context_instance=RequestContext(request, processors=[])
    )
