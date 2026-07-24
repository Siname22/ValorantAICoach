import functools
import importlib.resources

from .exceptions import PromptNotFound


class PromptLoader:
    """Utility to automatically load prompt.md files for agents."""

    @staticmethod
    @functools.lru_cache(maxsize=128)
    def load_prompt(agent_class: type) -> str:
        """
        Loads the prompt.md file located in the same package as the given
        agent class. Uses importlib.resources for robust loading, especially
        in packaged applications.
        The result is cached for performance.

        Args:
            agent_class: The class of the agent requesting its prompt.

        Returns:
            The content of the prompt.md file as a string.

        Raises:
            PromptNotFound: If the prompt.md file does not exist or cannot be read.
        """
        try:
            package_name = agent_class.__module__
            prompt_resource = importlib.resources.files(package_name).joinpath(
                "prompt.md"
            )
            return prompt_resource.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise PromptNotFound(
                f"Prompt file not found for {agent_class.__name__}: {e}"
            ) from e
        except Exception as e:
            raise PromptNotFound(
                f"Failed to load prompt for {agent_class.__name__}: {e}"
            ) from e
