#!/usr/bin/env python3
"""
Save match statistics to a file for later analysis.
"""

import os
import json
import datetime
import argparse
from typing import Dict, Any

def save_match_stats(stats: Dict[str, Any], output_dir: str = None, 
                    filename: str = None) -> str:
    """
    Save match statistics to a JSON file.
    
    Args:
        stats: The match statistics dictionary
        output_dir: Directory to save the file (defaults to 'match_stats')
        filename: Custom filename (defaults to timestamp-based name)
        
    Returns:
        Path to the saved file
    """
    # Create output directory if it doesn't exist
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'match_stats')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename if not provided
    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        map_name = stats.get("map", "unknown").lower().replace(" ", "_")
        score = stats.get("score", "0-0").replace("-", "_")
        filename = f"match_{map_name}_{score}_{timestamp}.json"
    
    # Ensure filename has .json extension
    if not filename.endswith('.json'):
        filename += '.json'
    
    # Full path to output file
    output_path = os.path.join(output_dir, filename)
    
    # Save stats to file
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Save match statistics to a file")
    parser.add_argument("stats_file", help="Path to match statistics JSON file or '-' for stdin")
    parser.add_argument("--output-dir", help="Directory to save the file", default=None)
    parser.add_argument("--filename", help="Custom filename", default=None)
    
    args = parser.parse_args()
    
    try:
        # Load stats from file or stdin
        if args.stats_file == '-':
            import sys
            stats = json.load(sys.stdin)
        else:
            with open(args.stats_file, 'r') as f:
                stats = json.load(f)
        
        # Save stats to file
        output_path = save_match_stats(stats, args.output_dir, args.filename)
        print(f"Match statistics saved to {output_path}")
            
    except FileNotFoundError:
        print(f"Error: File {args.stats_file} not found")
    except json.JSONDecodeError:
        print(f"Error: Input is not valid JSON")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 