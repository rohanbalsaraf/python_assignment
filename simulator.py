#imports
import json
import math
import csv
import sys
import random
import time
import argparse

#distance calculate
"""Calculate Euclidean distance between two points [x, y]"""
def calculate_distance(point1,point2):
    return math.hypot(point1[0]-point2[0],point1[1]-point2[1])

#prasing inputs
def prase_json(filepath):
    try:
        with open(filepath, r) as file:
            data = json.load(file)

        if isinstance(data.get('warehouse'),dict):
            warehouse = data ['warehouse']
        elif isinstance(data.get('warehouse'),list):
            warehouse[w['id']] = w['loaction']

        return warehouse,agents,packages

    except FileNotFoundError:
        print(f"Error: Could not find file {filepath}")
        sys.exit(1)

