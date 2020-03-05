#!/usr/bin/python3
from flask import Flask,make_response,request,jsonify
from flask import render_template,redirect,session
import json
import os
import time
from os.path import exists as path_exists
from os.path import join as path_join
import re
import logging
import sys
import subprocess as sp
import multiprocessing as mp
import redis

app = Flask(os.path.basename(os.getcwd()))
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key='sxlgkxk'
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
stat=dict()
stat['name']=os.path.basename(os.getcwd())
stat['ip']='http://127.0.0.1'
item_list,category_list=list(),list()

@app.route('/')
def index():
    return render_template('index.html',title='{}'.format(stat['name']),stat=stat,size=len(item_list),item_list=item_list,category_list=category_list,category='/')

@app.route('/v/<path:name>',methods=['POST','GET'])
def view_item(name):
    global item_list
    category=os.path.dirname(name)
    filename=os.path.basename(name)
    if request.method=='POST':
        text=request.form['text']
        with open('static/item/{}.md'.format(name),'w') as f:
            f.write(text)
        for item in item_list:
            if item['name'] == name:
                print('edit: {}'.format(name))
                item['edited']='True'
                db = redis.Redis()
                while db.get('blog_refreshing'):
                    time.sleep(0.01)
                db.set('blog_refreshing','running')
                with open('static/item_list.json','w') as f:
                    f.write(json.dumps({'list':item_list,'category_list':category_list}))
                db.delete('blog_refreshing')
                refreshFunc()
                break
    if request.method=='GET':
        if 'action' in request.args:
            with open('static/item/{}.md'.format(name),'r') as f:
                text=f.read()
            return render_template('edit.html',text=text,stat=stat,
                            category=os.path.dirname(name),
                            title='{}-Edit:{}'.format(stat['name'],os.path.basename(name)),
                            name=name,
                            filename=os.path.basename(name),
                            cur_category=os.path.dirname(name),
                            #category_list=category_list,
                            category_list=[x for x in  category_list if re.match('^{}/'.format(name),x['name']) or re.match('^{}/'.format(x['name']),name) or name==x['name']])
        if os.path.splitext(filename)[1] in ['.webp','.png','.jpg','.jpeg','.gif','.bmp']:
            return redirect('/static/media/image/{}'.format(filename.replace('_','/')))
    return render_template('_{}.html'.format(filename),
                            title='{}-{}'.format(stat['name'],os.path.basename(name)),
                            stat=stat,
                            name=filename,
                            category_list=category_list,
                            #category_list=[x for x in  category_list if re.match('^{}/'.format(name),x['name']) or re.match('^{}/'.format(x['name']),name) or name==x['name']]
                            cur_category=os.path.dirname(name))

@app.route('/c/<path:name>')
def view_category(name):
    _item_list=[x for x in item_list if re.match('^{}'.format(name), x['category'])]
    return render_template('index.html',stat=stat,
                            item_list=_item_list,
                            category_list=category_list,
                            title='{}-Category:{}'.format(stat['name'],os.path.basename(name)),
                            #category_list=[x for x in  category_list if re.match('^{}/'.format(name),x['name']) or re.match('^{}/'.format(x['name']),name) or name==x['name']],
                            cur_category_base=os.path.basename(name),
                            cur_category_dir=os.path.dirname(name),
                            size=len(_item_list),
                            cur_category=name)

def refreshFunc():
    global item_list,category_list

    db = redis.Redis()
    if db.get('blog_refreshing'):
        return
    db.set('blog_refreshing','running')
    db.expire('blog_refreshing', 60*30)

    with open('static/item_list.json','r') as f:
        tmp=json.loads(f.read())
        old_item_list=tmp['list']
        old_category_list=tmp['category_list']
    new_category_list=list()
    new_item_list=list()
    item_dict=dict()
    for item in old_item_list:
        item_dict[item['name']]=item
    category_dict=dict()

    for r, d, f in os.walk('static/item',followlinks=True):
        if os.path.basename(r)[0] in ['.', '_']:
            logging.info("folder[0] is '.' or '_', continue")
            continue
        category = r.replace('static/item/', '')
        if category == 'static/item':
            continue
        if category not in new_category_list:
            new_category_list.append(category)
            category_dict[category] = 0
        for file in f:
            if os.path.basename(file)[0] == '.':
                logging.info("filename[0] is '.' or '_', continue")
                continue
            if os.path.splitext(file)[-1] == '.md':
                category_dict[category]+=1
                path = os.path.abspath(path_join(r, file))
                mtime = os.stat(path).st_mtime
                filename = os.path.splitext(os.path.basename(file))[0]
                name=path_join(category,filename)
                htmlpath = 'templates/_{}.html'.format(filename)

                if name in item_dict:
                    if item_dict[name]['mtime'] == mtime:
                        if os.path.exists(htmlpath):
                            new_item_list.append(item_dict[name])
                            continue

                logging.info('use new \'{}\''.format(name))
                print('use new \'{}\''.format(name))
                with open(path,'r') as f:
                    line1=f.read().split('\n')[0]
                    if 'abbr' in line1:
                        abbr=line1.replace('abbr','').lstrip(' :')
                    else:
                        abbr=''

                if name in item_dict:
                    if 'edited' in item_dict[name]:
                        editedStatus=item_dict[name]['edited']
                    else:
                        editedStatus='False'
                else:
                    editedStatus='False'
                item = {'name': name,
                        'filename':filename,
                        'category': category,
                        'abbr': abbr,
                        'mtime': mtime,
                        'edited': editedStatus}
                new_item_list.append(item)

                html_content = sp.getoutput('pandoc {} --mathjax -s -f markdown -t html'.format(path))
                with open(htmlpath, 'w') as f:
                    header = "<h1><a href='/c/{category}'>{category} </a> {filename} <i class='fas fa-edit btn_edit' style='color: #ddd' name='/v/{name}?action=edit' onclick='window.location.href=this.getAttribute(\"name\")'></i></h1><hr/>".format(filename=filename,category=category,name=name)
                    f.write('{% extends "layout.html" %}{% block body %}'+header + html_content + '{% endblock %}')

    new_item_list.sort(key=lambda x: x['mtime'],reverse=True)
    item_list=new_item_list
    category_list=[{'name':x,'size':category_dict[x],'fullsize': sum([category_dict[y] for y in new_category_list if re.match('^{}'.format(x),y)]) } for x in new_category_list]
    category_list.sort(key=lambda x: x['name'])
    with open('static/item_list.json','w') as f:
        f.write(json.dumps({'list':item_list,'category_list':category_list}))

    db.delete('blog_refreshing')

@app.route('/search')
def search():
    keys=request.args['keys'].split(' ')
    itemlist=item_list
    for key in keys:
        itemlist=[x for x in itemlist if key in x['name'] or key in x['abbr']]

    return jsonify(itemlist=itemlist)

def main_processor():
    while True:
        time.sleep(1)
        status=sp.getoutput('curl http://127.0.0.1:5000/refresh')

@app.route('/refresh')
def refresh():
    global item_list
    if 'action' in request.args:
        for item in item_list:
            item['edited']='False'
    with open('static/item_list.json','w') as f:
        f.write(json.dumps({'list':item_list,'category_list':category_list}))
    refreshFunc()
    return redirect('/')

def app_init():
    p=mp.Process(target=main_processor)
    p.start()
    db=redis.Redis()
    db.delete('blog_refreshing')
    refreshFunc()

app_init()
#app.run(debug=True,host="0.0.0.0",port=5000,use_reloader=False)
