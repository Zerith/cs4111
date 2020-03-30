#!/usr/bin/env python2.7

"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver

To run locally:

    python server.py

Go to http://localhost:8111 in your browser.

A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort, jsonify

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@104.196.18.7/w4111
#
# For example, if you had username biliris and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://biliris:foobar@104.196.18.7/w4111"
#
# DATABASEURI = "postgresql://user:password@104.196.18.7/w4111"
DATABASEURI = "postgresql://postgres:postgres@127.0.0.1/HW2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#

# Preload the list of domains
DomainList = [domain[0] for domain in engine.execute("SELECT name FROM domain")]
OrganizationList = [org[0] for org in engine.execute("SELECT name FROM Organization")]
IPList = [ip[0] for ip in engine.execute("SELECT ip FROM Endpoint")]


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

#
@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """
  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html")

#
# This is an example of a different path.  You can see it at:
# 
#     localhost:8111/another
#
# Notice that the function name is another() rather than index()
# The functions for each app.route need to have different names


@app.route('/getDomainList')
def getDomainlist():
  return jsonify(DomainList)


@app.route('/getDomainData')
def getDomainData():
  domain = request.args.get('domain')
  result = engine.execute(text("SELECT A.ip FROM AssociatedDomain A WHERE A.DomainName = :domain"), domain=domain)
  endpoint_ips = [row[0] for row in result]

  endpoints = []
  for ip in endpoint_ips:
    endpoints.append(getEndpointInfo(ip))

  domainData = {'name': domain, 'endpoints': endpoints}
  return jsonify(domainData)


def getOpenPortsForIP(ip):
  result = engine.execute(text("SELECT Ex.PortNumber, Ex.PortType, I.ServiceName FROM ExposesPort Ex, Implements I"
  " WHERE Ex.IP = :ip AND I.PortNumber = Ex.PortNumber AND I.PortType = Ex.PortType"), ip=ip)
  result =  list(result)
  openPorts = [
      {
        'number': row[0],
        'type':   row[1],
        'serviceName':  row[2]
      } for row in result
  ]

  return openPorts

def getEndpointInfo(ip):
  result = engine.execute(text("SELECT O.ip, O.OrgName, A.domainname, L.city, L.country, L.latitude, L.longitude FROM OwnsEndpoint O, LocatedIn L, AssociatedDomain A"
  " WHERE A.ip = :ip AND A.ip = O.ip AND L.ip = O.ip"), ip=ip)
  result = list(result)[0]

  endpointInfo = {
    'IP':       result[0],
    'org':      result[1],
    'domain':   result[2],
    'location': {'city': result[3], 'country': result[4], 'latitute': result[5], 'longtitude': result[6]}
  }

  # Get open oprts fo rthe Endpoitn
  endpointInfo['openPorts'] = getOpenPortsForIP(ip)
  return endpointInfo

# export interface Endpoint {
#     IP          : string
#     location    : Location
#     openPorts   : Port[]
#     domain      : string
# }
@app.route('/getEndpointData')
def getEndpointData():
  # Get Endpoint Information
  ip = request.args.get('ip')
  endpointInfo = getEndpointInfo(ip)

  return jsonify(endpointInfo)

@app.route('/getOrgData')
def getOrgData():
  orgname = request.args.get('org')
  result = engine.execute(text("SELECT O.ip FROM OwnsEndpoint O WHERE O.OrgName = :name"), name=orgname)
  endpoint_ips = [row[0] for row in result]

  endpoints = []
  for ip in endpoint_ips:
    endpoints.append(getEndpointInfo(ip))

  orgData = {'name': orgname, 'endpoints': endpoints}
  return jsonify(orgData)

@app.route('/getOrgList')
def getOrgList():
  return jsonify(OrganizationList)

@app.route('/getIPList')
def getIPList():
  return jsonify(IPList)

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
