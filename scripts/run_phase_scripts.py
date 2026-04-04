#!/usr/bin/env python
"""
Phase-aware script runner

Detects current season phase and runs appropriate scripts.
Used by GitHub Actions workflow to eliminate commented-out scripts.
"""

import sys
import subprocess
import logging
from season_phase import detect_season_phase
from phase_config import get_scripts_for_phase, get_phase_description

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_script(script_path):
    """Run a single Python script and return success/failure"""
    try:
        logging.info(f"Running: {script_path}")
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per script
        )
        
        if result.returncode == 0:
            logging.info(f"✅ Success: {script_path}")
            # Log stdout if it contains useful info
            if result.stdout and result.stdout.strip():
                for line in result.stdout.strip().split('\n')[-10:]:  # Last 10 lines
                    if 'Fetching game' in line or 'Successfully fetched' in line or 'Uploaded combined' in line:
                        logging.info(f"   {line}")
            return True
        else:
            logging.error(f"❌ Failed: {script_path}")
            logging.error(f"   stderr: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logging.error(f"⏱️  Timeout: {script_path}")
        return False
    except Exception as e:
        logging.error(f"❌ Error running {script_path}: {e}")
        return False

def main(override_phase=None):
    """
    Main runner that detects phase and executes appropriate scripts
    
    Args:
        override_phase: Optional manual phase override ('regular_season', 'postseason', 'offseason')
    """
    # Detect phase (or use override)
    if override_phase:
        phase = override_phase
        postseason_active = (phase == "postseason")
        season_year = None  # Not needed for override
        logging.info(f"Using manual phase override: {phase}")
    else:
        phase, postseason_active, season_year = detect_season_phase()
    
    # Get scripts for this phase
    scripts = get_scripts_for_phase(phase)
    description = get_phase_description(phase)
    
    logging.info(f"\n{'='*60}")
    logging.info(f"Phase-Aware Script Runner")
    logging.info(f"{'='*60}")
    logging.info(f"Phase: {phase}")
    logging.info(f"Description: {description}")
    logging.info(f"Scripts to run: {len(scripts)}")
    logging.info(f"{'='*60}\n")
    
    # Run scripts
    success_count = 0
    fail_count = 0
    
    for script in scripts:
        success = run_script(script)
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    logging.info(f"\n{'='*60}")
    logging.info(f"Summary")
    logging.info(f"{'='*60}")
    logging.info(f"✅ Successful: {success_count}")
    logging.info(f"❌ Failed: {fail_count}")
    logging.info(f"{'='*60}\n")
    
    # Exit with error if any failures
    if fail_count > 0:
        logging.error(f"Exiting with error code 1 ({fail_count} scripts failed)")
        sys.exit(1)
    
    logging.info("All scripts completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    # Allow phase override via command line
    override = None
    if len(sys.argv) > 1:
        override = sys.argv[1]
        if override not in ["regular_season", "postseason", "offseason"]:
            print(f"Invalid phase: {override}")
            print("Usage: python run_phase_scripts.py [regular_season|postseason|offseason]")
            sys.exit(1)
    
    main(override_phase=override)
