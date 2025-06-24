"""
Locust-based load testing for GovStack API
"""
import random
import json
import time
from uuid import uuid4
from typing import Dict, Any, List
import httpx
from locust import HttpUser, task, between, events
from locust.env import Environment

from ..config import config
from ..utils.monitoring import PerformanceMonitor
from ..utils.token_tracker import TokenTracker

class GovStackUser(HttpUser):
    """Simulates a user interacting with the GovStack API"""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Initialize user session"""
        self.session_id = str(uuid4())
        self.user_id = f"load_test_user_{uuid4()}"
        self.query_count = 0
        self.token_tracker = TokenTracker()
        
    @task(3)
    def chat_with_api(self):
        """Simulate chat interaction - most common task"""
        query = random.choice(config.sample_queries)
        
        payload = {
            "message": query,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "metadata": {
                "test_type": "load_test",
                "query_count": self.query_count
            }
        }
        
        start_time = time.time()
        
        with self.client.post(
            "/chat/",
            json=payload,
            timeout=config.api_timeout,
            catch_response=True
        ) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Track token usage if available
                    if config.track_token_usage and 'usage' in data and data['usage']:
                        self.token_tracker.track_usage(data['usage'])
                    
                    # Check response quality
                    if len(data.get('answer', '')) < 10:
                        response.failure(f"Response too short: {data.get('answer', '')}")
                    elif response_time > config.max_response_time_ms:
                        response.failure(f"Response time too high: {response_time}ms")
                    else:
                        response.success()
                        
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
        
        self.query_count += 1
    
    @task(1)
    def get_chat_history(self):
        """Get chat history - less frequent task"""
        with self.client.get(
            f"/chat/{self.session_id}",
            timeout=config.api_timeout,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Expected if no chat history exists yet
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_health_check(self):
        """Health check endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

class ConcurrentChatUser(HttpUser):
    """Simulates users having longer conversations"""
    
    wait_time = between(2, 8)
    
    def on_start(self):
        self.session_id = str(uuid4())
        self.user_id = f"concurrent_user_{uuid4()}"
        self.conversation_count = 0
        
    @task
    def have_conversation(self):
        """Simulate a multi-turn conversation"""
        queries = [
            "What services are available for business registration?",
            "What are the required documents?",
            "How long does the process take?",
            "What are the fees involved?",
            "Can I track my application status?"
        ]
        
        for i, query in enumerate(queries):
            if i > 0:
                # Add some delay between messages in conversation
                self.wait()
            
            payload = {
                "message": query,
                "session_id": self.session_id,
                "user_id": self.user_id,
                "metadata": {
                    "test_type": "concurrent_conversation",
                    "conversation_turn": i + 1
                }
            }
            
            with self.client.post(
                "/chat/",
                json=payload,
                timeout=config.api_timeout,
                catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"HTTP {response.status_code}")
                    break  # Exit conversation on error
                else:
                    response.success()
        
        self.conversation_count += 1


# Event listeners for monitoring
@events.request.add_listener
def request_handler(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Log request details for analysis"""
    if hasattr(context, 'locust') and hasattr(context.locust, 'environment'):
        # Log to performance monitor if available
        pass

@events.test_start.add_listener
def test_start_handler(environment, **kwargs):
    """Initialize monitoring when test starts"""
    print(f"Load test starting with {environment.parsed_options.num_users} users")
    print(f"Target URL: {environment.host}")

@events.test_stop.add_listener  
def test_stop_handler(environment, **kwargs):
    """Clean up when test stops"""
    print("Load test completed")
    
    # Print summary statistics
    if hasattr(environment, 'stats'):
        stats = environment.stats
        print(f"\nTest Summary:")
        print(f"Total requests: {stats.total.num_requests}")
        print(f"Total failures: {stats.total.num_failures}")
        print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
        print(f"Max response time: {stats.total.max_response_time:.2f}ms")
        print(f"Requests per second: {stats.total.current_rps:.2f}")
        print(f"Failure rate: {(stats.total.num_failures / max(1, stats.total.num_requests)) * 100:.2f}%")


class StressTestUser(HttpUser):
    """High-intensity user for stress testing"""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    def on_start(self):
        self.session_id = str(uuid4())
        self.user_id = f"stress_user_{uuid4()}"
        
    @task
    def rapid_fire_requests(self):
        """Send requests rapidly to test system limits"""
        query = random.choice(config.sample_queries)
        
        payload = {
            "message": query,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "metadata": {"test_type": "stress_test"}
        }
        
        with self.client.post(
            "/chat/",
            json=payload,
            timeout=5,  # Shorter timeout for stress test
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


if __name__ == "__main__":
    # Run the load test directly
    from locust import run_single_user
    run_single_user(GovStackUser)
