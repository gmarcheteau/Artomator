#!/usr/bin/env python

import urllib
import json
import os
import time
import matplotlib.pyplot as plt
import ArtyFarty.bsgenerator as bs
import ArtyFarty.bsgenerator_en as bs_en
import ArtyFarty.drawing as drawing
import ArtyFarty.imageapp as imageapp
import ArtyFarty.sendemail as sendemail
import ArtyFarty.receivemail as receivemail
import twitterutils.tweet_processor as tweet_processor
import StringIO
import resource
from rq import Queue
from worker import conn

from flask import Flask
from flask import request,make_response,render_template,redirect,url_for

from app import app
from forms import URLForm

from config import DEFAULT_URL

q = Queue(connection=conn)

@app.route('/getbs', methods=['GET'])
def getBS():
  comment = bs.generatePhrase()
  return render_template("getbs.html",comment=comment)

@app.route('/news', methods=['GET'])
def goNews():
  return render_template("news.html")

@app.route('/')
@app.route('/getbs_en', methods=['GET'])
def getBS_en():
  comment = bs_en.generatePhrase()
  return render_template("getbs.html",comment=comment)


@app.route('/getbs_img', methods=['GET','POST'])
def getBS_img():
  #DEFAULT_URL = "http://www.telegraph.co.uk/content/dam/art/2016/10/04/picasso-large_trans++qVzuuqpFlyLIwiB6NTmJwbKTcqHAsmNzJMPMiov7fpk.jpg"
  
  imageurl = request.args.get('imageurl', default=DEFAULT_URL)
  #remove quotes in url if any
  imageurl = imageurl.strip('"').strip('\'')
  if not imageurl.startswith("http"):
    imageurl = DEFAULT_URL
  
  #number of clusters to use --TODO: do something with it
  number_clusters = request.args.get('clusters', default=5)
  
  form = URLForm()
  if form.validate_on_submit():
    # [...]
    print "input URL: %s" %form.url.data
    try:
      return redirect(url_for('getBS_img',imageurl = form.url.data))
    except Exception as err:
      print "error in form bit -- %s" %str(err)
  
  #imageBS is a dict with all you need to create the HTML resp
  imageBS = produceImageBS(imageurl)
  
  return render_template("getbs_img.html",
                imagecomment = imageBS["imagecomment"],
                imageurl = imageBS["imageurl"],
                maincolorstrings = imageBS["maincolorstrings"],
                score = imageBS["score"],
                colorboxes = imageBS["colorboxes"],
                simplerimage = imageBS["simplerimage"],
                form = form)
  
def produceImageBS(imageurl):
  import base64
  
  #if receiving a local image, add full path
  if not imageurl.startswith("http"):
    print "appending full path to url"
    imageurl = os.path.abspath(imageurl)
  
  #get data from image comment (comment, colors, drawn colors)
  #REDIS enqueue blocking function
  #imageresponse = imageapp.commentOnImage(imageurl)
  
  job = q.enqueue(imageapp.commentOnImage,imageurl)
  # TODO: how long to wait?
  while not job.result:
    imageresponse = ''
  imageresponse = job.result
  
  print '(from views.py) Memory usage: %s (kb)' % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
  
  imagecomment = imageresponse["comment"]
  maincolorstrings = imageresponse["maincolorstrings"]
  score = imageresponse["score"]
  colorboxes = imageresponse["colorboxes"]
  simplerimage = imageresponse["simplerimage"]
  
  #return dict with all values to generate HTML response
  #provides ability to choose template independently
  return {
    "imagecomment" : imagecomment,
    "imageurl" : imageurl,
    "maincolorstrings" : maincolorstrings,
    "score" : score,
    "colorboxes" : colorboxes,
    "simplerimage" : simplerimage
    }

@app.route('/getbs_img_multi', methods=['GET','POST'])
def getBS_img_multi():
  import base64
  
  DEFAULT_URL = "http://www.telegraph.co.uk/content/dam/art/2016/10/04/picasso-large_trans++qVzuuqpFlyLIwiB6NTmJwbKTcqHAsmNzJMPMiov7fpk.jpg"
  
  imageurl = request.args.get('imageurl', default=DEFAULT_URL)
  #remove quotes in url if any
  imageurl = imageurl.strip('"').strip('\'')
  if not imageurl.startswith("http"):
    imageurl = DEFAULT_URL
  
  #number of clustering versions to show
  number_iter = request.args.get('iter', default=5, type=int)
  
  #SHOW_SIMPLER_IMAGES config from url
  SHOW_SIMPLER_IMAGES = request.args.get('show_simpler_images', default=False, type=bool)
  print "SHOW_SIMPLER_IMAGES --", str(SHOW_SIMPLER_IMAGES)
  
  #get data from image comment (comment, colors, drawn colors)
  #imageresponse = imageapp.commentOnImageFullMode(imageurl,number_iter,SHOW_SIMPLER_IMAGES)
  #REDIS enqueue blocking function
  #imageresponse = imageapp.commentOnImage(imageurl)

  job = q.enqueue(
    imageapp.commentOnImageFullMode,
    imageurl,number_iter,SHOW_SIMPLER_IMAGES
    )
  # TODO: how long to wait?
  while not job.result:
    imageresponse = ''
  imageresponse = job.result
  
  imagecomment = imageresponse["comment"]
  maincolorstringslist = imageresponse["maincolorstringslist"]
  silhouettescores = imageresponse["silhouettescores"]
  colorboxes = imageresponse["colorboxes"]
  simplerimages = imageresponse["simplerimages"]
  
  print "len(simplerimages):", len(simplerimages)
  
  print silhouettescores
  print len(silhouettescores)
  
  form = URLForm()
  if form.validate_on_submit():
    # [...]
    print "input URL: %s" %form.url.data
    return redirect(url_for('getBS_img_multi',imageurl = form.url.data))
  
  return render_template("getbs_img_multi.html",
                imagecomment = imagecomment,
                imageurl = imageurl,
                maincolorstringslist = maincolorstringslist,
                silhouettescores = silhouettescores,
                colorboxes = colorboxes,
                simplerimages = simplerimages,
                SHOW_SIMPLER_IMAGES = SHOW_SIMPLER_IMAGES,
                form = form)

@app.route('/getbs_img_url', methods=["GET", "POST"])
def getURL():
    form = URLForm()
    if form.validate_on_submit():
        # [...]

        print "input URL: %s" %form.url.data
        return redirect(url_for('getBS_img',imageurl = form.url.data))
    return render_template('enterurl.html', form=form)

@app.route('/checkmail', methods=['GET','POST'])
def checkmail():
 
  newMessages = receivemail.checkNewMailWithImages()
  for message in newMessages:
    imageurl = os.path.abspath(message["imageurl"])
    print "imageurl sent to generator: %s" %imageurl
    sendMailAboutImage(
      imageurl=imageurl,
      toaddr=message["fromaddr"])
  return "<h2>Found and analysed %d image(s)</h2>" %len(newMessages)
  

defaulttoaddr = "gregoire.marcheteau@gmail.com"
def sendMailAboutImage(imageurl,toaddr=defaulttoaddr):
  #toaddr = request.args.get('email', default=defaulttoaddr)
  
  #imageBS is a dict with all you need to create the HTML resp
  imageBS = produceImageBS(imageurl)
  
  htmlmessage = render_template("getbs_img_mail.html",
                imagecomment = imageBS["imagecomment"],
                imageurl = "http://localhostimage"+imageBS["imageurl"],
                maincolorstrings = imageBS["maincolorstrings"],
                score = imageBS["score"],
                colorboxes = imageBS["colorboxes"],
                simplerimage = imageBS["simplerimage"],
                form = imageBS["form"])
  print "http://localhostimage"+imageBS["imageurl"]
  sendemail.sendEmail(htmlmessage,toaddr)
  
@app.route('/tweet', methods=['GET','POST'])
def tweetCheck():
  #try and find latest tweet processed
  try:
    filename = "latest_tweet_id.txt"
    file = open(filename, "r")
    LATEST_TWEET_PROCESSED = int(file.read())
    file.close()
    
  except Exception as err:
    LATEST_TWEET_PROCESSED = 822387055162335234
    print "Error opening %s -- %s" %(filename,str(err))
  
  #check for new tweets and process them (e.g. save and reply)
  twitter_response = tweet_processor.checkTweetsAndReply(LATEST_TWEET_PROCESSED)
  
  #app.config.update(
  #  LATEST_TWEET_PROCESSED=twitter_response["latest_tweet_id"])
  
  return "<h2>Found %d tweet(s)</h2><hr><p>Results: %s" %(twitter_response["number_tweets"],twitter_response["process_responses"])
  