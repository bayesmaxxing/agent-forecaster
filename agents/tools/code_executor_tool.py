from agents.utils.code_executor import CodeExecutor
from .base import Tool



class CodeExecutorTool(Tool):
    def __init__(self):
        super().__init__(
            name="code_executor",
            description="Executes code in a container. The code must be in Python and it can only use the following libraries: numpy, pandas, scipy, statsmodels.",
            input_schema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The code to execute. It must be in Python and it can only use the following libraries: numpy, pandas, scipy, statsmodels.",
                    },
                },
                "required": ["code"],
            },
        )
        self.code_executor = CodeExecutor()

    async def execute(self, code: str) -> str:
        result = self.code_executor.execute_code(code)
        return result["stdout"]
    

if __name__ == "__main__":
    code_executor_tool = CodeExecutorTool()
    result = code_executor_tool.execute("print('Hello, world!')")
    print(result)