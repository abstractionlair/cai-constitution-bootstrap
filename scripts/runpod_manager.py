#!/usr/bin/env python3
"""
RunPod Management Helper
Provides cost-conscious pod management for the CAI experiment
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any

class RunPodManager:
    """Manage RunPod instances with cost tracking"""
    
    def __init__(self):
        self.api_key = os.getenv('RUNPOD_API_KEY')
        self.api_url = 'https://api.runpod.io/graphql'
        self.headers = {}
        
        if self.api_key:
            self.headers = {'Authorization': f'Bearer {self.api_key}'}
        
        # Cost tracking - A100 SXM 80GB
        self.hourly_rate = 1.74
        self.start_time = None
        
    def check_credentials(self) -> bool:
        """Check if RunPod API credentials are set"""
        if not self.api_key:
            print("⚠️  RUNPOD_API_KEY not found in environment")
            print("Please add to .env.runpod:")
            print("RUNPOD_API_KEY=your_api_key_here")
            return False
        return True
    
    def list_pods(self) -> Optional[list]:
        """List all pods for the account"""
        if not self.check_credentials():
            return None
            
        query = '''
        query {
            myself {
                pods {
                    id
                    name
                    status
                    gpuType
                    costPerHr
                    runtime
                }
            }
        }
        '''
        
        response = requests.post(
            self.api_url,
            json={'query': query},
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('myself', {}).get('pods', [])
        return None
    
    def stop_pod(self, pod_id: str) -> bool:
        """Stop a running pod to save costs"""
        if not self.check_credentials():
            return False
            
        query = f'''
        mutation {{
            podStop(input: {{podId: "{pod_id}"}}) {{
                id
                status
            }}
        }}
        '''
        
        response = requests.post(
            self.api_url,
            json={'query': query},
            headers=self.headers
        )
        
        if response.status_code == 200:
            print(f"✅ Pod {pod_id} stopped successfully")
            return True
        else:
            print(f"❌ Failed to stop pod: {response.text}")
            return False
    
    def start_pod(self, pod_id: str) -> bool:
        """Start a stopped pod"""
        if not self.check_credentials():
            return False
            
        query = f'''
        mutation {{
            podResume(input: {{podId: "{pod_id}"}}) {{
                id
                status
                machine {{
                    ip
                    sshPort
                }}
            }}
        }}
        '''
        
        response = requests.post(
            self.api_url,
            json={'query': query},
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            pod = data.get('data', {}).get('podResume', {})
            if pod:
                print(f"✅ Pod {pod_id} started")
                machine = pod.get('machine', {})
                if machine:
                    print(f"SSH: ssh root@{machine.get('ip')} -p {machine.get('sshPort')}")
                return True
        
        print(f"❌ Failed to start pod: {response.text}")
        return False
    
    def estimate_cost(self, hours: float) -> float:
        """Estimate cost for given hours"""
        return hours * self.hourly_rate
    
    def log_session_start(self):
        """Log session start for cost tracking"""
        self.start_time = datetime.now()
        with open('logs/runpod_sessions.log', 'a') as f:
            f.write(f"Session started: {self.start_time.isoformat()}\n")
        print(f"📊 Session started at {self.start_time.strftime('%H:%M:%S')}")
        print(f"💰 Estimated cost: ${self.hourly_rate:.2f}/hour")
    
    def log_session_end(self):
        """Log session end and calculate cost"""
        if not self.start_time:
            self.start_time = datetime.now()
            
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds() / 3600
        cost = self.estimate_cost(duration)
        
        with open('logs/runpod_sessions.log', 'a') as f:
            f.write(f"Session ended: {end_time.isoformat()}\n")
            f.write(f"Duration: {duration:.2f} hours\n")
            f.write(f"Estimated cost: ${cost:.2f}\n")
            f.write("-" * 40 + "\n")
        
        print(f"📊 Session duration: {duration:.2f} hours")
        print(f"💰 Estimated cost: ${cost:.2f}")
        
        return duration, cost


def main():
    """CLI interface for RunPod management"""
    manager = RunPodManager()
    
    if len(sys.argv) < 2:
        print("Usage: python runpod_manager.py [command]")
        print("Commands:")
        print("  list    - List all pods")
        print("  stop    - Stop a pod")
        print("  start   - Start a pod")
        print("  cost    - Estimate cost for N hours")
        print("  begin   - Log session start")
        print("  end     - Log session end")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        pods = manager.list_pods()
        if pods:
            print("\n📦 Your RunPod instances:")
            for pod in pods:
                status = "🟢" if pod['status'] == 'RUNNING' else "🔴"
                print(f"{status} {pod['name']} ({pod['id']})")
                print(f"   GPU: {pod['gpuType']}, Cost: ${pod.get('costPerHr', 0):.2f}/hr")
                if pod.get('runtime'):
                    print(f"   Runtime: {pod['runtime']} seconds")
            print()
    
    elif command == "stop":
        if len(sys.argv) < 3:
            print("Usage: python runpod_manager.py stop [pod_id]")
            return
        pod_id = sys.argv[2]
        manager.stop_pod(pod_id)
    
    elif command == "start":
        if len(sys.argv) < 3:
            print("Usage: python runpod_manager.py start [pod_id]")
            return
        pod_id = sys.argv[2]
        manager.start_pod(pod_id)
    
    elif command == "cost":
        if len(sys.argv) < 3:
            print("Usage: python runpod_manager.py cost [hours]")
            return
        hours = float(sys.argv[2])
        cost = manager.estimate_cost(hours)
        print(f"💰 Estimated cost for {hours} hours: ${cost:.2f}")
    
    elif command == "begin":
        manager.log_session_start()
    
    elif command == "end":
        manager.log_session_end()
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
