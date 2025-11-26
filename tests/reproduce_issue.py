import sys
import os
import shutil
import json
from datetime import datetime, timezone

# Add app to path
sys.path.append(os.getcwd())

from app.services.report_service import compute_summary
from app.storage import ensure_plan_dir, append_metrics_line

def reproduce():
    plan_id = 9999
    
    # 1. Clean up previous test data
    plan_dir = f"data/plan_{plan_id}"
    if os.path.exists(plan_dir):
        shutil.rmtree(plan_dir)
    
    # 2. Simulate cumulative data for one member
    # Member 1 moves: 1km -> 2km -> 3km (Total should be 3km)
    member_id = 1
    
    records = [
        {"plan_id": plan_id, "member_id": member_id, "distance_km": 1.0, "travel_minutes": 10, "late_minutes": 0, "wait_minutes": 0},
        {"plan_id": plan_id, "member_id": member_id, "distance_km": 2.0, "travel_minutes": 20, "late_minutes": 0, "wait_minutes": 0},
        {"plan_id": plan_id, "member_id": member_id, "distance_km": 3.0, "travel_minutes": 30, "late_minutes": 0, "wait_minutes": 0},
    ]
    
    print(f"Injecting {len(records)} cumulative records for plan {plan_id}...")
    for r in records:
        append_metrics_line(plan_id, r)
        
    # 3. Compute summary
    print("Computing summary...")
    summary = compute_summary(plan_id)
    
    # 4. Check results
    total_dist = summary["overall"]["total_distance_km"]
    total_min = summary["overall"]["total_travel_minutes"]
    
    print(f"Total Distance: {total_dist} km")
    print(f"Total Minutes: {total_min} min")
    
    # Expected: 3.0 km (max), 30 min (max)
    # Actual (Bug): 6.0 km (sum), 60 min (sum)
    
    if total_dist == 6.0:
        print("✅ Issue Reproduced: Distance is summed (1+2+3=6) instead of max (3).")
    elif total_dist == 3.0:
        print("❌ Issue Not Reproduced: Distance is correct (3).")
    else:
        print(f"❓ Unexpected Result: {total_dist}")

if __name__ == "__main__":
    reproduce()
