"""
Desktop integration tools.
"""
import asyncio
from typing import Optional

from pydantic import BaseModel, Field

from ..core.types import ToolInput, ToolResult, ToolMetadata, ToolException
from .base import BaseTool


class NotificationInput(ToolInput):
    """Input for desktop notification tool."""
    title: str = Field(..., description="Notification title", max_length=100)
    message: str = Field(..., description="Notification message", max_length=500)
    urgency: str = Field(default="normal", description="Notification urgency level", pattern="^(low|normal|critical)$")
    timeout: Optional[int] = Field(default=None, description="Timeout in milliseconds", ge=0, le=30000)


class NotificationResult(ToolResult):
    """Result from desktop notification."""
    notification_id: Optional[str] = None


class DesktopNotificationTool(BaseTool):
    """Tool for sending desktop notifications via notify-send."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="send_desktop_notification",
            description="Send a desktop notification to the user using the system notification daemon",
            input_schema=NotificationInput,
            output_schema=NotificationResult,
            category="desktop",
            tags=["notification", "desktop", "alert"]
        )
    
    async def execute(self, input_data: NotificationInput) -> NotificationResult:
        """Execute the desktop notification."""
        try:
            # Build notify-send command
            cmd = ["notify-send"]
            
            # Add urgency level
            cmd.extend(["-u", input_data.urgency])
            
            # Add timeout if specified
            if input_data.timeout is not None:
                cmd.extend(["-t", str(input_data.timeout)])
            
            # Add title and message
            cmd.extend([input_data.title, input_data.message])
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_message = stderr.decode().strip() if stderr else f"Process exited with code {process.returncode}"
                raise ToolException(f"Failed to send notification: {error_message}")
            
            return NotificationResult(
                success=True,
                message=f"Successfully sent notification: '{input_data.title}'",
                data={"title": input_data.title, "message": input_data.message}
            )
            
        except FileNotFoundError:
            raise ToolException(
                "notify-send command not found. Please install libnotify or ensure it's in your PATH."
            )
        except Exception as e:
            raise ToolException(f"Unexpected error sending notification: {e}")


class SystemCommandTool(BaseTool):
    """Tool for executing safe system commands."""
    
    # Whitelist of allowed commands for security
    ALLOWED_COMMANDS = {
        "date": ["date"],
        "uptime": ["uptime"],
        "whoami": ["whoami"],
        "pwd": ["pwd"],
        "ls": ["ls", "-la"],
        "disk_usage": ["df", "-h"],
        "memory_info": ["free", "-h"],
        "system_info": ["uname", "-a"]
    }
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="execute_system_command",
            description="Execute safe system commands to get system information",
            input_schema=self._get_input_schema(),
            category="system",
            tags=["system", "command", "info"]
        )
    
    def _get_input_schema(self):
        """Create dynamic input schema based on allowed commands."""
        from enum import Enum
        
        # Create enum of allowed commands
        CommandEnum = Enum('CommandEnum', {cmd: cmd for cmd in self.ALLOWED_COMMANDS.keys()})
        
        class SystemCommandInput(ToolInput):
            command: CommandEnum = Field(..., description="System command to execute")
        
        return SystemCommandInput
    
    async def execute(self, input_data) -> ToolResult:
        """Execute the system command."""
        command_name = input_data.command.value
        
        if command_name not in self.ALLOWED_COMMANDS:
            raise ToolException(f"Command not allowed: {command_name}")
        
        cmd_args = self.ALLOWED_COMMANDS[command_name]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_message = stderr.decode().strip() if stderr else f"Command failed with code {process.returncode}"
                raise ToolException(f"Command execution failed: {error_message}")
            
            output = stdout.decode().strip()
            
            return ToolResult(
                success=True,
                message=f"Command '{command_name}' executed successfully",
                data={"command": command_name, "output": output}
            )
            
        except FileNotFoundError:
            raise ToolException(f"Command not found: {cmd_args[0]}")
        except Exception as e:
            raise ToolException(f"Unexpected error executing command: {e}")