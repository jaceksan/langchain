import json
from typing import Any, Dict, Generator, Iterator, List, Optional, Union

import requests
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.llms import LLM
from langchain_core.outputs import GenerationChunk
from langchain_core.pydantic_v1 import Extra, root_validator
from langchain_core.utils import get_from_dict_or_env


class SVEndpointHandler:
    """
    SambaNova Systems Interface for Sambaverse endpoint.

    :param str host_url: Base URL of the DaaS API service
    """

    API_BASE_PATH = "/api/predict"

    def __init__(self, host_url: str):
        """
        Initialize the SVEndpointHandler.

        :param str host_url: Base URL of the DaaS API service
        """
        self.host_url = host_url
        self.http_session = requests.Session()

    @staticmethod
    def _process_response(response: requests.Response) -> Dict:
        """
        Processes the API response and returns the resulting dict.

        All resulting dicts, regardless of success or failure, will contain the
        `status_code` key with the API response status code.

        If the API returned an error, the resulting dict will contain the key
        `detail` with the error message.

        If the API call was successful, the resulting dict will contain the key
        `data` with the response data.

        :param requests.Response response: the response object to process
        :return: the response dict
        :rtype: dict
        """
        result: Dict[str, Any] = {}
        try:
            text_result = response.text.strip().split("\n")[-1]
            result = {"data": json.loads("".join(text_result.split("data: ")[1:]))}
        except Exception as e:
            result["detail"] = str(e)
        if "status_code" not in result:
            result["status_code"] = response.status_code
        return result

    @staticmethod
    def _process_streaming_response(
        response: requests.Response,
    ) -> Generator[GenerationChunk, None, None]:
        """Process the streaming response"""
        try:
            import sseclient
        except ImportError:
            raise ValueError(
                "could not import sseclient library"
                "Please install it with `pip install sseclient-py`."
            )
        client = sseclient.SSEClient(response)
        close_conn = False
        for event in client.events():
            if event.event == "error_event":
                close_conn = True
            text = json.dumps({"event": event.event, "data": event.data})
            chunk = GenerationChunk(text=text)
            yield chunk
        if close_conn:
            client.close()

    def _get_full_url(self) -> str:
        """
        Return the full API URL for a given path.
        :returns: the full API URL for the sub-path
        :rtype: str
        """
        return f"{self.host_url}{self.API_BASE_PATH}"

    def nlp_predict(
        self,
        key: str,
        sambaverse_model_name: Optional[str],
        input: Union[List[str], str],
        params: Optional[str] = "",
        stream: bool = False,
    ) -> Dict:
        """
        NLP predict using inline input string.

        :param str project: Project ID in which the endpoint exists
        :param str endpoint: Endpoint ID
        :param str key: API Key
        :param str input_str: Input string
        :param str params: Input params string
        :returns: Prediction results
        :rtype: dict
        """
        if isinstance(input, str):
            input = [input]
        parsed_input = []
        for element in input:
            parsed_element = {
                "conversation_id": "sambaverse-conversation-id",
                "messages": [
                    {
                        "message_id": 0,
                        "role": "user",
                        "content": element,
                    }
                ],
            }
            parsed_input.append(json.dumps(parsed_element))
        if params:
            data = {"inputs": parsed_input, "params": json.loads(params)}
        else:
            data = {"inputs": parsed_input}
        response = self.http_session.post(
            self._get_full_url(),
            headers={
                "key": key,
                "Content-Type": "application/json",
                "modelName": sambaverse_model_name,
            },
            json=data,
        )
        return SVEndpointHandler._process_response(response)

    def nlp_predict_stream(
        self,
        key: str,
        sambaverse_model_name: Optional[str],
        input: Union[List[str], str],
        params: Optional[str] = "",
    ) -> Iterator[GenerationChunk]:
        """
        NLP predict using inline input string.

        :param str project: Project ID in which the endpoint exists
        :param str endpoint: Endpoint ID
        :param str key: API Key
        :param str input_str: Input string
        :param str params: Input params string
        :returns: Prediction results
        :rtype: dict
        """
        if isinstance(input, str):
            input = [input]
        parsed_input = []
        for element in input:
            parsed_element = {
                "conversation_id": "sambaverse-conversation-id",
                "messages": [
                    {
                        "message_id": 0,
                        "role": "user",
                        "content": element,
                    }
                ],
            }
            parsed_input.append(json.dumps(parsed_element))
        if params:
            data = {"inputs": parsed_input, "params": json.loads(params)}
        else:
            data = {"inputs": parsed_input}
        # Streaming output
        response = self.http_session.post(
            self._get_full_url(),
            headers={
                "key": key,
                "Content-Type": "application/json",
                "modelName": sambaverse_model_name,
            },
            json=data,
            stream=True,
        )
        for chunk in SVEndpointHandler._process_streaming_response(response):
            yield chunk


class Sambaverse(LLM):
    """
    Sambaverse large language models.

    To use, you should have the environment variable ``SAMBAVERSE_API_KEY``
    set with your API key.

    get one in https://sambaverse.sambanova.ai
    read extra documentation in https://docs.sambanova.ai/sambaverse/latest/index.html


    Example:
    .. code-block:: python

        from langchain_community.llms.sambanova  import Sambaverse
        Sambaverse(
            sambaverse_url="https://sambaverse.sambanova.ai",
            sambaverse_api_key: "your sambaverse api key",
            sambaverse_model_name: "Meta/llama-2-7b-chat-hf",
            streaming: = False
            model_kwargs={
                "do_sample": False,
                "max_tokens_to_generate": 100,
                "temperature": 0.7,
                "top_p": 1.0,
                "repetition_penalty": 1,
                "top_k": 50,
            },
        )
    """

    sambaverse_url: str = "https://sambaverse.sambanova.ai"
    """Sambaverse url to use"""

    sambaverse_api_key: str = ""
    """sambaverse api key"""

    sambaverse_model_name: Optional[str] = None
    """sambaverse expert model to use"""

    model_kwargs: Optional[dict] = None
    """Key word arguments to pass to the model."""

    streaming: Optional[bool] = False
    """Streaming flag to get streamed response."""

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid

    @classmethod
    def is_lc_serializable(cls) -> bool:
        return True

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that api key exists in environment."""
        values["sambaverse_url"] = get_from_dict_or_env(
            values, "sambaverse_url", "SAMBAVERSE_URL"
        )
        values["sambaverse_api_key"] = get_from_dict_or_env(
            values, "sambaverse_api_key", "SAMBAVERSE_API_KEY"
        )
        values["sambaverse_model_name"] = get_from_dict_or_env(
            values, "sambaverse_model_name", "SAMBAVERSE_MODEL_NAME"
        )
        return values

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Get the identifying parameters."""
        return {**{"model_kwargs": self.model_kwargs}}

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "Sambaverse LLM"

    def _get_tuning_params(self, stop: Optional[List[str]]) -> str:
        """
        Get the tuning parameters to use when calling the LLM.

        Args:
            stop: Stop words to use when generating. Model output is cut off at the
                first occurrence of any of the stop substrings.

        Returns:
            The tuning parameters as a JSON string.
        """
        _model_kwargs = self.model_kwargs or {}
        _stop_sequences = _model_kwargs.get("stop_sequences", [])
        _stop_sequences = stop or _stop_sequences
        _model_kwargs["stop_sequences"] = ",".join(f'"{x}"' for x in _stop_sequences)
        tuning_params_dict = {
            k: {"type": type(v).__name__, "value": str(v)}
            for k, v in (_model_kwargs.items())
        }
        tuning_params = json.dumps(tuning_params_dict)
        return tuning_params

    def _handle_nlp_predict(
        self,
        sdk: SVEndpointHandler,
        prompt: Union[List[str], str],
        tuning_params: str,
    ) -> str:
        """
        Perform an NLP prediction using the Sambaverse endpoint handler.

        Args:
            sdk: The SVEndpointHandler to use for the prediction.
            prompt: The prompt to use for the prediction.
            tuning_params: The tuning parameters to use for the prediction.

        Returns:
            The prediction result.

        Raises:
            ValueError: If the prediction fails.
        """
        response = sdk.nlp_predict(
            self.sambaverse_api_key, self.sambaverse_model_name, prompt, tuning_params
        )
        if response["status_code"] != 200:
            optional_details = response["details"]
            optional_message = response["message"]
            raise ValueError(
                f"Sambanova /complete call failed with status code "
                f"{response['status_code']}. Details: {optional_details}"
                f"{response['status_code']}. Message: {optional_message}"
            )
        return response["data"]["completion"]

    def _handle_completion_requests(
        self, prompt: Union[List[str], str], stop: Optional[List[str]]
    ) -> str:
        """
        Perform a prediction using the Sambaverse endpoint handler.

        Args:
            prompt: The prompt to use for the prediction.
            stop: stop sequences.

        Returns:
            The prediction result.

        Raises:
            ValueError: If the prediction fails.
        """
        ss_endpoint = SVEndpointHandler(self.sambaverse_url)
        tuning_params = self._get_tuning_params(stop)
        return self._handle_nlp_predict(ss_endpoint, prompt, tuning_params)

    def _handle_nlp_predict_stream(
        self, sdk: SVEndpointHandler, prompt: Union[List[str], str], tuning_params: str
    ) -> Iterator[GenerationChunk]:
        """
        Perform a streaming request to the LLM.

        Args:
            sdk: The SVEndpointHandler to use for the prediction.
            prompt: The prompt to use for the prediction.
            tuning_params: The tuning parameters to use for the prediction.

        Returns:
            An iterator of GenerationChunks.
        """
        for chunk in sdk.nlp_predict_stream(
            self.sambaverse_api_key, self.sambaverse_model_name, prompt, tuning_params
        ):
            yield chunk

    def _stream(
        self,
        prompt: Union[List[str], str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """Stream the Sambaverse's LLM on the given prompt.

        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.
            run_manager: Callback manager for the run.
            **kwargs: Additional keyword arguments. directly passed
                to the sambaverse model in API call.

        Returns:
            An iterator of GenerationChunks.
        """
        ss_endpoint = SVEndpointHandler(self.sambaverse_url)
        tuning_params = self._get_tuning_params(stop)
        try:
            if self.streaming:
                for chunk in self._handle_nlp_predict_stream(
                    ss_endpoint, prompt, tuning_params
                ):
                    if run_manager:
                        run_manager.on_llm_new_token(chunk.text)
                    yield chunk
            else:
                return
        except Exception as e:
            # Handle any errors raised by the inference endpoint
            raise ValueError(f"Error raised by the inference endpoint: {e}") from e

    def _handle_stream_request(
        self,
        prompt: Union[List[str], str],
        stop: Optional[List[str]],
        run_manager: Optional[CallbackManagerForLLMRun],
        kwargs: Dict[str, Any],
    ) -> str:
        """
        Perform a streaming request to the LLM.

        Args:
            prompt: The prompt to generate from.
            stop: Stop words to use when generating. Model output is cut off at the
                first occurrence of any of the stop substrings.
            run_manager: Callback manager for the run.
            **kwargs: Additional keyword arguments. directly passed
                to the sambaverse model in API call.

        Returns:
            The model output as a string.
        """
        completion = ""
        for chunk in self._stream(
            prompt=prompt, stop=stop, run_manager=run_manager, **kwargs
        ):
            completion += chunk.text
        return completion

    def _call(
        self,
        prompt: Union[List[str], str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Run the LLM on the given input.

        Args:
            prompt: The prompt to generate from.
            stop: Stop words to use when generating. Model output is cut off at the
                first occurrence of any of the stop substrings.
            run_manager: Callback manager for the run.
            **kwargs: Additional keyword arguments. directly passed
                to the sambaverse model in API call.

        Returns:
            The model output as a string.
        """
        try:
            if self.streaming:
                return self._handle_stream_request(prompt, stop, run_manager, kwargs)
            return self._handle_completion_requests(prompt, stop)
        except Exception as e:
            # Handle any errors raised by the inference endpoint
            raise ValueError(f"Error raised by the inference endpoint: {e}") from e


class SSEndpointHandler:
    """
    SambaNova Systems Interface for SambaStudio model endpoints.

    :param str host_url: Base URL of the DaaS API service
    """

    API_BASE_PATH = "/api"

    def __init__(self, host_url: str):
        """
        Initialize the SSEndpointHandler.

        :param str host_url: Base URL of the DaaS API service
        """
        self.host_url = host_url
        self.http_session = requests.Session()

    @staticmethod
    def _process_response(response: requests.Response) -> Dict:
        """
        Processes the API response and returns the resulting dict.

        All resulting dicts, regardless of success or failure, will contain the
        `status_code` key with the API response status code.

        If the API returned an error, the resulting dict will contain the key
        `detail` with the error message.

        If the API call was successful, the resulting dict will contain the key
        `data` with the response data.

        :param requests.Response response: the response object to process
        :return: the response dict
        :rtype: dict
        """
        result: Dict[str, Any] = {}
        try:
            result = response.json()
        except Exception as e:
            result["detail"] = str(e)
        if "status_code" not in result:
            result["status_code"] = response.status_code
        return result

    @staticmethod
    def _process_streaming_response(
        response: requests.Response,
    ) -> Generator[GenerationChunk, None, None]:
        """Process the streaming response"""
        try:
            import sseclient
        except ImportError:
            raise ValueError(
                "could not import sseclient library"
                "Please install it with `pip install sseclient-py`."
            )
        client = sseclient.SSEClient(response)
        close_conn = False
        for event in client.events():
            if event.event == "error_event":
                close_conn = True
            text = json.dumps({"event": event.event, "data": event.data})
            chunk = GenerationChunk(text=text)
            yield chunk
        if close_conn:
            client.close()

    def _get_full_url(self, path: str) -> str:
        """
        Return the full API URL for a given path.

        :param str path: the sub-path
        :returns: the full API URL for the sub-path
        :rtype: str
        """
        return f"{self.host_url}{self.API_BASE_PATH}{path}"

    def nlp_predict(
        self,
        project: str,
        endpoint: str,
        key: str,
        input: Union[List[str], str],
        params: Optional[str] = "",
        stream: bool = False,
    ) -> Dict:
        """
        NLP predict using inline input string.

        :param str project: Project ID in which the endpoint exists
        :param str endpoint: Endpoint ID
        :param str key: API Key
        :param str input_str: Input string
        :param str params: Input params string
        :returns: Prediction results
        :rtype: dict
        """
        if isinstance(input, str):
            input = [input]
        if params:
            data = {"inputs": input, "params": json.loads(params)}
        else:
            data = {"inputs": input}
        response = self.http_session.post(
            self._get_full_url(f"/predict/nlp/{project}/{endpoint}"),
            headers={"key": key},
            json=data,
        )
        return SSEndpointHandler._process_response(response)

    def nlp_predict_stream(
        self,
        project: str,
        endpoint: str,
        key: str,
        input: Union[List[str], str],
        params: Optional[str] = "",
    ) -> Iterator[GenerationChunk]:
        """
        NLP predict using inline input string.

        :param str project: Project ID in which the endpoint exists
        :param str endpoint: Endpoint ID
        :param str key: API Key
        :param str input_str: Input string
        :param str params: Input params string
        :returns: Prediction results
        :rtype: dict
        """
        if isinstance(input, str):
            input = [input]
        if params:
            data = {"inputs": input, "params": json.loads(params)}
        else:
            data = {"inputs": input}
        # Streaming output
        response = self.http_session.post(
            self._get_full_url(f"/predict/nlp/stream/{project}/{endpoint}"),
            headers={"key": key},
            json=data,
            stream=True,
        )
        for chunk in SSEndpointHandler._process_streaming_response(response):
            yield chunk


class SambaStudio(LLM):
    """
    SambaStudio large language models.

    To use, you should have the environment variables
    ``SAMBASTUDIO_BASE_URL`` set with your SambaStudio environment URL.
    ``SAMBASTUDIO_PROJECT_ID`` set with your SambaStudio project ID.
    ``SAMBASTUDIO_ENDPOINT_ID`` set with your SambaStudio endpoint ID.
    ``SAMBASTUDIO_API_KEY``  set with your SambaStudio endpoint API key.

    https://sambanova.ai/products/enterprise-ai-platform-sambanova-suite

    read extra documentation in https://docs.sambanova.ai/sambastudio/latest/index.html

    Example:
    .. code-block:: python

        from langchain_community.llms.sambanova  import Sambaverse
        SambaStudio(
            base_url="your SambaStudio environment URL",
            project_id=set with your SambaStudio project ID.,
            endpoint_id=set with your SambaStudio endpoint ID.,
            api_token= set with your SambaStudio endpoint API key.,
            streaming=false
            model_kwargs={
                "do_sample": False,
                "max_tokens_to_generate": 1000,
                "temperature": 0.7,
                "top_p": 1.0,
                "repetition_penalty": 1,
                "top_k": 50,
            },
        )
    """

    base_url: str = ""
    """Base url to use"""

    project_id: str = ""
    """Project id on sambastudio for model"""

    endpoint_id: str = ""
    """endpoint id on sambastudio for model"""

    api_key: str = ""
    """sambastudio api key"""

    model_kwargs: Optional[dict] = None
    """Key word arguments to pass to the model."""

    streaming: Optional[bool] = False
    """Streaming flag to get streamed response."""

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid

    @classmethod
    def is_lc_serializable(cls) -> bool:
        return True

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Get the identifying parameters."""
        return {**{"model_kwargs": self.model_kwargs}}

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "Sambastudio LLM"

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that api key and python package exists in environment."""
        values["base_url"] = get_from_dict_or_env(
            values, "sambastudio_base_url", "SAMBASTUDIO_BASE_URL"
        )
        values["project_id"] = get_from_dict_or_env(
            values, "sambastudio_project_id", "SAMBASTUDIO_PROJECT_ID"
        )
        values["endpoint_id"] = get_from_dict_or_env(
            values, "sambastudio_endpoint_id", "SAMBASTUDIO_ENDPOINT_ID"
        )
        values["api_key"] = get_from_dict_or_env(
            values, "sambastudio_api_key", "SAMBASTUDIO_API_KEY"
        )
        return values

    def _get_tuning_params(self, stop: Optional[List[str]]) -> str:
        """
        Get the tuning parameters to use when calling the LLM.

        Args:
            stop: Stop words to use when generating. Model output is cut off at the
                first occurrence of any of the stop substrings.

        Returns:
            The tuning parameters as a JSON string.
        """
        _model_kwargs = self.model_kwargs or {}
        _stop_sequences = _model_kwargs.get("stop_sequences", [])
        _stop_sequences = stop or _stop_sequences
        # _model_kwargs['stop_sequences'] = ','.join(
        #     f"'{x}'" for x in _stop_sequences)
        tuning_params_dict = {
            k: {"type": type(v).__name__, "value": str(v)}
            for k, v in (_model_kwargs.items())
        }
        tuning_params = json.dumps(tuning_params_dict)
        return tuning_params

    def _handle_nlp_predict(
        self, sdk: SSEndpointHandler, prompt: Union[List[str], str], tuning_params: str
    ) -> str:
        """
        Perform an NLP prediction using the SambaStudio endpoint handler.

        Args:
            sdk: The SSEndpointHandler to use for the prediction.
            prompt: The prompt to use for the prediction.
            tuning_params: The tuning parameters to use for the prediction.

        Returns:
            The prediction result.

        Raises:
            ValueError: If the prediction fails.
        """
        response = sdk.nlp_predict(
            self.project_id, self.endpoint_id, self.api_key, prompt, tuning_params
        )
        if response["status_code"] != 200:
            optional_detail = response["detail"]
            raise ValueError(
                f"Sambanova /complete call failed with status code "
                f"{response['status_code']}. Details: {optional_detail}"
            )
        return response["data"][0]["completion"]

    def _handle_completion_requests(
        self, prompt: Union[List[str], str], stop: Optional[List[str]]
    ) -> str:
        """
        Perform a prediction using the SambaStudio endpoint handler.

        Args:
            prompt: The prompt to use for the prediction.
            stop: stop sequences.

        Returns:
            The prediction result.

        Raises:
            ValueError: If the prediction fails.
        """
        ss_endpoint = SSEndpointHandler(self.base_url)
        tuning_params = self._get_tuning_params(stop)
        return self._handle_nlp_predict(ss_endpoint, prompt, tuning_params)

    def _handle_nlp_predict_stream(
        self, sdk: SSEndpointHandler, prompt: Union[List[str], str], tuning_params: str
    ) -> Iterator[GenerationChunk]:
        """
        Perform a streaming request to the LLM.

        Args:
            sdk: The SVEndpointHandler to use for the prediction.
            prompt: The prompt to use for the prediction.
            tuning_params: The tuning parameters to use for the prediction.

        Returns:
            An iterator of GenerationChunks.
        """
        for chunk in sdk.nlp_predict_stream(
            self.project_id, self.endpoint_id, self.api_key, prompt, tuning_params
        ):
            yield chunk

    def _stream(
        self,
        prompt: Union[List[str], str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """Call out to Sambanova's complete endpoint.

        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.

        Returns:
            The string generated by the model.
        """
        ss_endpoint = SSEndpointHandler(self.base_url)
        tuning_params = self._get_tuning_params(stop)
        try:
            if self.streaming:
                for chunk in self._handle_nlp_predict_stream(
                    ss_endpoint, prompt, tuning_params
                ):
                    if run_manager:
                        run_manager.on_llm_new_token(chunk.text)
                    yield chunk
            else:
                return
        except Exception as e:
            # Handle any errors raised by the inference endpoint
            raise ValueError(f"Error raised by the inference endpoint: {e}") from e

    def _handle_stream_request(
        self,
        prompt: Union[List[str], str],
        stop: Optional[List[str]],
        run_manager: Optional[CallbackManagerForLLMRun],
        kwargs: Dict[str, Any],
    ) -> str:
        """
        Perform a streaming request to the LLM.

        Args:
            prompt: The prompt to generate from.
            stop: Stop words to use when generating. Model output is cut off at the
                first occurrence of any of the stop substrings.
            run_manager: Callback manager for the run.
            **kwargs: Additional keyword arguments. directly passed
                to the sambaverse model in API call.

        Returns:
            The model output as a string.
        """
        completion = ""
        for chunk in self._stream(
            prompt=prompt, stop=stop, run_manager=run_manager, **kwargs
        ):
            completion += chunk.text
        return completion

    def _call(
        self,
        prompt: Union[List[str], str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call out to Sambanova's complete endpoint.

        Args:
            prompt: The prompt to pass into the model.
            stop: Optional list of stop words to use when generating.

        Returns:
            The string generated by the model.
        """
        if stop is not None:
            raise Exception("stop not implemented")
        try:
            if self.streaming:
                return self._handle_stream_request(prompt, stop, run_manager, kwargs)
            return self._handle_completion_requests(prompt, stop)
        except Exception as e:
            # Handle any errors raised by the inference endpoint
            raise ValueError(f"Error raised by the inference endpoint: {e}") from e
