from locust import HttpUser, between, task


class EuroGrantUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def check_health(self):
        self.client.get("/health")

    @task(3)
    def search_grants(self):
        # /grants/search is a POST that requires authentication. Without
        # credentials it returns 401; we treat that as a reachable response so
        # the load test measures the routing + auth path latency rather than
        # reporting every request as a failure. To load-test the full search
        # path, authenticate in on_start() and attach the token here.
        with self.client.post(
            "/api/v1/grants/search",
            json={"query": "AI research", "limit": 10},
            name="/grants/search",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 401):
                response.success()
