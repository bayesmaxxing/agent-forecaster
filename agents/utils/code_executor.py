import docker

class CodeExecutor:
    def __init__(self):
        self.client = self.client = docker.DockerClient(
            base_url='unix:///Users/samuelsvensson/.colima/default/docker.sock'
        )
        self.image = "forecasting-agent:latest"

    def execute_code(self, code: str, timeout: int = 60) -> str:
        container = self.client.containers.run(
            self.image,
            command=["python", "-c", code],
            detach=True,
            mem_limit="1g",
            network_disabled=True,
            remove=False,
            stdout=True,
            stderr=True,
        )

        # wait for execution
        result = container.wait(timeout=timeout)

        output = container.logs(stdout=True, stderr=False).decode("utf-8")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
        
        # Remove container after execution
        container.remove()

        return {
            "success": result["StatusCode"] == 0,
            "stdout": output,
            "stderr": stderr,
            "exit_code": result["StatusCode"],
        }


if __name__ == "__main__":
    code_executor = CodeExecutor()
    result = code_executor.execute_code("import numpy as np; print(np.random.randint(0, 100))")
    print(result)