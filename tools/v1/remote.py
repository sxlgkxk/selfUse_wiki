#!/usr/bin/python3
import json
import os
from os.path import join as path_join

os.chdir('/root/repo/psite/blog/tools')
# os.chdir('/home/gkxk/repo/release/blog/tools')
blog_item_folder='../static/item'
local_post_list_path= '../static/local_post_list.json'
remote_post_list_path= '../static/remote_post_list.json'
templates_folder='../templates'

with open(local_post_list_path,'r') as f:
    posts_list=json.loads(f.read())['list']
    tmp=dict()
    for post in posts_list:
        tmp.update({post['name']:post})
    posts_dict=tmp

for r, d, f in os.walk(blog_item_folder):
    for file in f:
        if os.path.splitext(file)[-1]=='.md':
            folder=os.path.relpath(r).replace('../static/item/','')
            path=os.path.abspath(path_join(r, file))
            filename=os.path.splitext(os.path.basename(file))[0]
            name=path_join(folder,filename)
            if name not in posts_dict:
                os.remove(path)
                path=path_join(templates_folder,'_{}.html'.format(name))
                try:
                    pass
                    os.remove(path)
                except:
                    pass
                print('rm {}'.format(name))

remote_item_list=list()
for item in posts_dict.values():
    path=path_join(blog_item_folder,item['name']+'.md')
    print('lack {}'.format(path))
    if not os.path.exists(path):
        remote_item_list.append(item['name'])

with open(path_join(remote_post_list_path),'w') as f:
    f.write(json.dumps(remote_item_list))