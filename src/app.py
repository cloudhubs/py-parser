#!/usr/bin/env python3

import jsonpickle
from flask import Flask
from flask import request
from src.parser import parse_source_file
from src.interface import system_interfaces


app = Flask(__name__)


@app.route('/')
def hello_world():
    # Handshake Endpoint
    return 'Hello I\'m PyParser!'


@app.route('/parse', methods=['POST'])
def parser():
    # Generates a parsed tree for a project
    request_data = request.get_json()
    results = parse_source_file(request_data['fileName'])
    return app.response_class(
        response=jsonpickle.encode(results, unpicklable=False),
        status=200,
        mimetype='application/json'
    )


@app.route('/interface', methods=['POST'])
def interface():
    # Generates interfaces for a project
    request_data = request.get_json()
    results = system_interfaces(request_data['fileName'])
    return app.response_class(
        response=jsonpickle.encode(results, unpicklable=False),
        status=200,
        mimetype='application/json'
    )


if __name__ == '__main__':
    app.run()
