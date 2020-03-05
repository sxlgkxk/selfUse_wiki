#!/usr/bin/python3
import json
import os
import sys
from os.path import join as path_join
import subprocess as sp
import markdown
import requests
import shutil
import re
import time
import redis
import logging

#status=requests.get('http://www.baidu.com').status_code
status=requests.get('http://icanhazip.com').status_code
if status != 200:
    sys.exit()

os.chdir('/home/gkxk/repo/release/blog/tools')

logging.basicConfig(
        filename="app.log",
        level=logging.INFO,
        format='%(levelname)s:%(asctime)s:%(message)s'
        )
db=redis.Redis()
if db.get('blog_uploading'):
    sys.exit()
db.set('blog_uploading','running')
db.expire('blog_uploading',60*30)

is_changed=False
blog_md_folder=os.path.abspath('../static/item')
local_post_list_path=os.path.abspath('../static/local_post_list.json')
remote_post_list_path=os.path.abspath('../static/remote_post_list.json')
github_md_folder='../../../git/sxlgkxk.github.io/source/_posts'
old_posts,new_posts,folder_list=list(),list(),list()

with open(local_post_list_path, 'r') as f:
    content=json.loads(f.read())
    old_posts=content['list']
    old_folder_list=content['folder_list']
    tmp=dict()
    for post in old_posts:
        tmp.update({post['name']:post})
    old_posts_dict=tmp

for r, d, f in os.walk(blog_md_folder):
    if os.path.basename(r)[0] in ['.','_']:
        logging.info("folder[0] is '.' or '_', continue")
        continue
    for file in f:
        if os.path.basename(file)[0]=='.':
            logging.info("filename[0] is '.' or '_', continue")
            continue
        if os.path.splitext(file)[-1]=='.md':
            folder=os.path.relpath(r).replace('../static/item/','')

            if not folder in old_folder_list:
                cmd = 'ssh root@108.160.135.157 "/root/repo/psite/blog/tools/check.py {}"'.format(
                    r.replace('/home/gkxk/repo/release/blog', '/root/repo/psite/blog').replace(' ', '\ ')).replace('(',
                                                                                                                   '\(').replace(
                    ')', '\)').replace("'", "\\'")
                status = sp.getoutput(cmd)
                logging.info("create '{}' if not existed status: {}".format(os.path.relpath(r), status))
                print("create '{}' if not existed status: {}".format(os.path.relpath(r), status))
                old_folder_list.append(folder)

            if not folder in folder_list:
                folder_list.append(folder)
            path=os.path.abspath(path_join(r, file))
            filename=os.path.splitext(os.path.basename(file))[0]
            name=path_join(folder,filename)
            mtime=os.stat(path_join(r,file)).st_mtime

            if name in old_posts_dict:
                if old_posts_dict[name]['mtime']==mtime:
                    new_posts.append(old_posts_dict[name])
                    print('use old \'{}\''.format(name))
                    continue

            with open(path,'r') as f:
                content=f.read()
            post={'name':name,
                  'folder':folder,
                  'mtime':mtime}
            print('use new \'{}\''.format(name))
            logging.info('use new \'{}\''.format(name))
            is_changed=True

            if re.match('^tech/',folder):
                with open(path_join(github_md_folder,file),'w') as f:
                    header='---\ntitle: {title}\n'.format(title=filename)
                    t=time.localtime(os.stat(path).st_ctime)
                    header=header+'date: {date}\n'.format(date=time.strftime('%Y/%m/%d %H:%M:%S',t))
                    t=time.localtime(os.stat(path).st_mtime)
                    header=header+'updated: {date}\n'.format(date=time.strftime('%Y/%m/%d %H:%M:%S',t))
                    header=header+'categories:\n- {}\n---\n'.format(folder)
                    f.write(header+content)

            status=sp.getoutput('scp {} root@108.160.135.157:{}'.format(path, path.replace('/home/gkxk/repo/release/blog',
                                                                                    '/root/repo/psite/blog')))
            new_posts.append(post)
            with open(local_post_list_path, 'w') as f:
                f.write(json.dumps({'list':new_posts,'folder_list':folder_list}))

new_posts.sort(key=lambda x:x['mtime'],reverse=True)

with open(local_post_list_path, 'w') as f:
    f.write(json.dumps({'list':new_posts,'folder_list':folder_list}))

if is_changed:
    status=sp.getoutput('scp {} root@108.160.135.157:{}'.format(local_post_list_path, local_post_list_path.replace('/home/gkxk/repo/release/blog',
                                                                                    '/root/repo/psite/blog')))
    os.chdir('/home/gkxk/repo/git/sxlgkxk.github.io')
    status = sp.getoutput('git checkout hexo')
    status = sp.getoutput('git add * && git commit -m "add text" && git push origin hexo')
    status = sp.getoutput('curl http://108.160.135.157:5000/refresh')

while True:
    status=sp.getoutput('ssh root@108.160.135.157 "python3 /root/repo/psite/blog/tools/remote.py"')
    status = sp.getoutput('scp root@108.160.135.157:{} {}'.format(remote_post_list_path.replace('/home/gkxk/repo/release/blog',
                                                                                       '/root/repo/psite/blog'),remote_post_list_path))
    with open(remote_post_list_path,'r') as f:
        remote_item_list=json.loads(f.read())
    if remote_item_list == []:
        break
    for name in remote_item_list:
        path = path_join(blog_md_folder, name + '.md')
        status = sp.getoutput('scp {} root@108.160.135.157:{}'.format(path, path.replace('/home/gkxk/repo/release/blog',
                                                                                         '/root/repo/psite/blog')))
        print('fix lack: {}'.format(path))
    status = sp.getoutput('curl http://108.160.135.157:5000/refresh')
    status=sp.getoutput('scp {} root@108.160.135.157:{}'.format(local_post_list_path, local_post_list_path.replace('/home/gkxk/repo/release/blog',
                                                                                    '/root/repo/psite/blog')))

db.delete('blog_uploading')
