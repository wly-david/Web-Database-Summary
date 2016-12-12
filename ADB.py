import urllib2
import base64
import json
import sys
import os.path
import subprocess
import re
import collections
import time

def database_classify(api_key, host, t_es, t_ec, ans, cetagory, rate, last_set, ans_list):
  queries = get_queries(cetagory.lower() + '.txt')
  doc_coverage = {}
  total_num = 0.0;
  link_set = set()
  for q in queries:
    results = get_search_result(api_key, q, host)
    total_num += int(results['WebTotal'])
    add_links(results['Web'], link_set)
    if queries[q] in doc_coverage:
      doc_coverage[queries[q]] += int(results['WebTotal'])
    else:
      doc_coverage[queries[q]] = int(results['WebTotal'])
  doc_specificity = {}
  for c in doc_coverage :
    doc_specificity[c] = doc_coverage[c] / total_num * rate
  print 'Coverage:'
  print doc_coverage
  print 'Specificity:'
  print doc_specificity
  classified = False
  for c in doc_coverage :
    if doc_coverage[c] > t_ec and doc_specificity[c] > t_es:
      classified = True
      if not os.path.exists(c.lower() + '.txt'):
        ans_list.append(ans + '/' + c)
      else:
        database_classify(api_key, host, t_es, t_ec, ans + '/' + c, c, doc_specificity[c], link_set, ans_list)
  if not classified:
    ans_list.append(ans)
  last_set |= link_set
  generate_summary(cetagory, host, link_set)
  return ans_list
def generate_summary(cetagory, host, link_set):
  print "Generating summary of " + cetagory + '-' + host
  filename = cetagory + '-' + host + '.txt';
  file_writer = open(filename, 'w')
  word_freq = {}
  print "Total link number: " + str(len(link_set))
  count = 0
  for link in link_set:
    print "get page: " + link
    words = get_words_from_url(link)
    if len(words) > 0:
      count += 1
    for word in words:
      if word in word_freq:
        word_freq[word] += 1
      else:
        word_freq[word] = 1  
  print "Total obtained link number: " + str(count)
  for word in sorted(word_freq.iterkeys()):
    file_writer.write(word +'#' + str(word_freq[word]) + '\n')
  file_writer.close();
  return
      
def add_links(results, link_set):
  for entry in results:
    link_set.add(entry['Url'].encode('utf8'))

def get_queries(file_name):
  dicts = {}
  with open(file_name,'r') as inf:
    for line in inf:
        words = line.rstrip('\n').split(' ', 1)
        dicts[words[1]] = words[0]
  return dicts

def get_search_result(api_key, search_content, host):
  search_content_encode = search_content.replace(' ','%20')
  bingUrl = "https://api.datamarket.azure.com/Data.ashx/Bing/SearchWeb/v1/Composite?Query=%27site%3a"\
            +host\
            +"%20"\
            +search_content_encode\
            +"%27&$top=4&$format=json"
  #Provide your account key here
  accountKey = api_key

  accountKeyEnc = base64.b64encode(accountKey + ':' + accountKey)
  headers = {'Authorization': 'Basic ' + accountKeyEnc}
  req = urllib2.Request(bingUrl, headers = headers)
  response = urllib2.urlopen(req)
  content = response.read()
  content_json = json.loads(content)
  return  content_json['d']['results'][0]

def get_words_from_url(url):
  req = urllib2.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' })
  count = 0
  while True:
    try:
      response = urllib2.urlopen(req)
      time.sleep(2)
    except Exception:
      print "failed to check the page type."
      count += 1
      if count == 5:
        return set()
      continue;
    break
  http_message = response.info()
  main = http_message.maintype
  if main != "text":
  #if url.endswith('.pdf'):
    return set()
  count = 0
  while True:
    try:
      str = subprocess.check_output(['java', 'getWordsLynx', url])
      #str = subprocess.check_output(['lynx', '--dump', url])
      time.sleep(2)
    except Exception:
      print "failed to fetch the page."
      count += 1
      if count == 3:
        return set()
      continue
    break
  str = re.sub("[\[\]\,]", "",  str)
#  str = str.split('References\n', 1)[0]
#  str = re.sub("\[[^\]]*\]", "",  str).lower()
#  str = re.sub("[^a-z]+", " ",  str)
  doc = str.split()
  return set(doc)
  
if __name__ == "__main__":
  if len(sys.argv) != 5:
      print "Should pass exactly 4 arguments: api_key, specificity threshold, coverage threshold and host URL"
      sys.exit(1)
  api_key = sys.argv[1]
  t_es = float(sys.argv[2])
  t_ec = int(sys.argv[3])
  host = sys.argv[4]

  if t_es <= 0 or t_es > 1:
      print "Specificity threshold must be a number greater than 0 and smaller or equal to 1"
      sys.exit(1)
  if not isinstance(t_ec, (int, long)) or t_ec <= 0:
    print "total number of docs should be a positive integer"

  ans = database_classify(api_key, host, t_es, t_ec, 'root', 'root', 1.0, set(), [])
  print "Classfication results of '" + host + "':"
  for str in ans:
    print str
  