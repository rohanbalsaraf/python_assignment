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
def parse_json(filepath):
    try:
        with open(filepath, 'r') as file:
            data = json.load(file)

        # Handle both list and dict formats for agents
        if isinstance(data.get('agents'),list):
            agents = {a['id']:a['location'] for a in data['agents']}
        elif isinstance(data.get('agents'),dict):
            agents = data['agents']
        else:
            print("Error: Invalid format for 'agents' in JSON file")
            sys.exit(1)

        # Handle both list and dict formats for warehouses
        if isinstance(data.get('warehouses'),list):
            warehouse = {w['id']:w['location'] for w in data['warehouses']}
        elif isinstance(data.get('warehouses'),dict):
            warehouse = data['warehouses']
        else:            
            print("Error: Invalid format for 'warehouses' in JSON file")
            sys.exit(1)

        # Handle both warehouse_id and warehouse field names in packages
        if isinstance(data.get('packages'),list):
            packages = data['packages']
            # Normalize package field names
            for pkg in packages:
                if 'warehouse_id' in pkg and 'warehouse' not in pkg:
                    pkg['warehouse'] = pkg.pop('warehouse_id')
        else:
            print("Error: Invalid format for 'packages' in JSON file")
            sys.exit(1)

        return warehouse,agents,packages

    except FileNotFoundError:
        print(f"Error: Could not find file {filepath}")
        sys.exit(1)
    
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in file {filepath}")
        sys.exit(1)
#logic
def assign_packages(warehouse,agents,packages):
    assignments = {a_id:[] for a_id in agents}
    for package in packages:
        w_loc = warehouse[package['warehouse']]
        nearest_agent = None
        min_distance = float('inf')

        for a_id, a_loc in agents.items():
            dist = calculate_distance(a_loc,w_loc)
            if dist < min_distance:
                min_distance = dist
                nearest_agent = a_id

        if nearest_agent:
            assignments[nearest_agent].append(package)

    return assignments

#exporter
def export_to_performer(report, best_agent):
    """Write a simple CSV with the best performer summary."""
    try:
        with open('performer.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['best_agent'])
            writer.writerow([best_agent if best_agent is not None else ''])
    except Exception:
        pass

#simulation_loop



#main
def main():
    #cli setup
    parser = argparse.ArgumentParser(description="delivery system simulator")
    parser.add_argument("input_file",help="Path to the JSON input file")
    parser.add_argument("--delays",action="store_true",help="Enable random delays in delivery times")
    parser.add_argument("--ascii",action="store_true",help="Output results in ASCII format instead of CSV")
    parser.add_argument("--midday-agent",action="store_true",help="Simulate an agent that starts work at midday")

    args = parser.parse_args()

    #extract
    warehouse,agents,packages = parse_json(args.input_file)
    print(f"Loaded {len(agents)} agents, {len(packages)} packages, and {len(warehouse)} warehouses from {args.input_file}")

    #transform
    if args.midday_agent:
        print("Simulating midday agent...")
        half = len(agents) // 2
        packages_morning = packages[:half]
        packages_afternoon = packages[half:]
        assignments_morning = assign_packages(warehouse,agents,packages_morning)
        agents['A_NEW'] = [50,50]
        assignments_afternoon = assign_packages(warehouse,agents,packages_afternoon)

        assignments = {a_id: [] for a_id in agents}
        for a_id, pkgs in assignments_morning.items():
            assignments[a_id].extend(pkgs)
        for a_id, pkgs in assignments_afternoon.items():
            assignments[a_id].extend(pkgs)
    else:
        assignments = assign_packages(warehouse,agents,packages)

    # prepare report container
    report = {}

    best_agent = None
    best_efficiency = float('inf')
    for a_id, pkgs in assignments.items():
        packages_delivered = len(pkgs)
        total_distance = sum(calculate_distance(agents[a_id], warehouse[pkg['warehouse']]) for pkg in pkgs)
        efficiency = total_distance / packages_delivered if packages_delivered > 0 else float('inf')
        
        if packages_delivered > 0 and efficiency < best_efficiency:
            best_efficiency = efficiency
            best_agent = a_id
    report["best_agent"] = best_agent

    #load
    with open('report.json','w') as f:
        json.dump(report,f,indent=2)

    print(f"\nSimulation Complete! Report saved to report.json")
    print("Final Report:")
    print(json.dumps(report,indent=2))

    export_to_performer(report,best_agent)


if __name__ == '__main__':
    main()