#imports
import json
import math
import csv
import sys
import random
import time
import argparse
import os
from pathlib import Path

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

#simulation function
def run_simulation(input_file, args, is_batch=False):
    """Run simulation for a single input file"""
    #extract
    warehouse,agents,packages = parse_json(input_file)
    print(f"Loaded {len(agents)} agents, {len(packages)} packages, and {len(warehouse)} warehouses from {input_file}")

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
        total_distance = 0
        total_time = 0
        
        # Start at agent's initial location
        current_loc = agents[a_id]
        
        if args.ascii and packages_delivered > 0:
            print(f"\n--- Route Visualization for {a_id} ---")
            print(f"Start: {current_loc}")
        
        for pkg in pkgs:
            w_loc = warehouse[pkg['warehouse']]
            dest_loc = pkg['destination']
            
            # Travel from current location to the warehouse
            dist_to_w = calculate_distance(current_loc, w_loc)
            # Travel from warehouse to package destination
            dist_to_dest = calculate_distance(w_loc, dest_loc)
            
            trip_dist = dist_to_w + dist_to_dest
            total_distance += trip_dist
            
            # Time is equivalent to distance, plus any delays
            trip_time = trip_dist
            delay = 0
            if args.delays:
                delay = round(random.uniform(1.0, 10.0), 2)
                trip_time += delay
            
            total_time += trip_time
            
            if args.ascii:
                print(f"  ──> {w_loc} (Pickup W: {pkg['warehouse']}) [dist: {dist_to_w:.2f}]")
                if args.delays:
                    print(f"      ... random delay of {delay} added ...")
                print(f"  ──> {dest_loc} (Deliver Pkg: {pkg['id']}) [dist: {dist_to_dest:.2f}]")
            
            # Agent finishes this delivery at the destination
            current_loc = dest_loc
            
        efficiency = total_distance / packages_delivered if packages_delivered > 0 else float('inf')
        
        # Use 0 instead of Infinity for standard JSON compliance
        report_efficiency = round(efficiency, 2) if packages_delivered > 0 else 0
        
        report[a_id] = {
            "packages_delivered": packages_delivered,
            "total_distance": round(total_distance, 2),
            "total_time": round(total_time, 2),
            "efficiency": report_efficiency
        }
        
        if packages_delivered > 0 and efficiency < best_efficiency:
            best_efficiency = efficiency
            best_agent = a_id
            
    report["best_agent"] = best_agent

    #load
    if not is_batch:
        with open('report.json','w') as f:
            json.dump(report,f,indent=2)
        print(f"Simulation Complete! Report saved to report.json")
    else:
        print(f"Simulation Complete!")
    print("Final Report:")
    print(json.dumps(report,indent=2))

    if not is_batch:
        export_to_performer(report,best_agent)
    return report, best_agent



#main
def main():
    #cli setup
    parser = argparse.ArgumentParser(description="delivery system simulator")
    parser.add_argument("input_file",help="Path to the JSON input file or folder containing JSON files")
    parser.add_argument("--delays",action="store_true",help="Enable random delays in delivery times")
    parser.add_argument("--ascii",action="store_true",help="Output results in ASCII format instead of CSV")
    parser.add_argument("--midday-agent",action="store_true",help="Simulate an agent that starts work at midday")

    args = parser.parse_args()

    input_path = Path(args.input_file)
    
    # Check if input is a directory
    if input_path.is_dir():
        print(f"\nRunning all JSON files in directory: {args.input_file}\n")
        json_files = sorted(input_path.glob('*.json'))
        
        if not json_files:
            print(f"Error: No JSON files found in {args.input_file}")
            sys.exit(1)
        
        results = []
        for json_file in json_files:
            print(f"\n{'='*60}")
            print(f"Processing: {json_file.name}")
            print(f"{'='*60}")
            try:
                report, best_agent = run_simulation(str(json_file), args, is_batch=True)
                results.append({
                    'file': json_file.name,
                    'best_agent': best_agent
                })
            except Exception as e:
                print(f"Error processing {json_file.name}: {e}")
                results.append({
                    'file': json_file.name,
                    'best_agent': 'ERROR'
                })
        
        # Print summary
        print(f"\n{'='*60}")
        print("SUMMARY OF ALL TEST CASES")
        print(f"{'='*60}")
        for i, result in enumerate(results, 1):
            print(f"Test Case {i:2d} ({result['file']:20s}): Best Agent = {result['best_agent']}")
        
        # Save batch results to JSON
        batch_report = {
            "total_test_cases": len(results),
            "test_results": results
        }
        with open('batch_report.json', 'w') as f:
            json.dump(batch_report, f, indent=2)
        print(f"\n✓ Batch report saved to: batch_report.json")
        
        # Save batch results to CSV
        with open('batch_summary.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Test Case', 'Best Agent'])
            for i, result in enumerate(results, 1):
                writer.writerow([result['file'], result['best_agent']])
        print(f"✓ Batch summary saved to: batch_summary.csv")
        
    else:
        # Single file mode
        run_simulation(args.input_file, args)


if __name__ == '__main__':
    main()