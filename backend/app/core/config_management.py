"""Core module for Kubernetes ConfigMap and deployment management."""

import logging
import time
from typing import Any, Dict, Optional

import yaml
from fastapi import HTTPException, status
from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

logger = logging.getLogger(__name__)


def get_current_namespace() -> str:
    """Get the current Kubernetes namespace."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            return f.read().strip()
    except Exception:
        return "default"


def get_configmap(namespace: str, configmap_name: str) -> tuple[Any, dict]:
    """Get ConfigMap and parse its YAML configuration."""
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    core_v1 = k8s_client.CoreV1Api()

    try:
        configmap = core_v1.read_namespaced_config_map(
            name=configmap_name, namespace=namespace
        )
    except k8s_client.ApiException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ConfigMap '{configmap_name}' not found in namespace '{namespace}'",
            )
        raise

    if "config.yaml" not in configmap.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ConfigMap does not contain 'config.yaml' key",
        )

    yaml_content = yaml.safe_load(configmap.data["config.yaml"])
    logger.info(f"Successfully loaded ConfigMap '{configmap_name}'")

    return configmap, yaml_content


def update_yaml_config(
    yaml_content: dict,
    provider_id: str,
    provider_type: str,
    provider_config: Dict[str, Any],
    model_id: str,
    metadata: Optional[Dict[str, Any]],
) -> dict:
    """Update YAML configuration with new provider and model."""
    if "providers" not in yaml_content:
        yaml_content["providers"] = {}

    # Providers are organized by API type (inference, safety, etc.)
    # For now, we'll add inference providers
    if "inference" not in yaml_content["providers"]:
        yaml_content["providers"]["inference"] = []

    # Check if provider already exists
    existing_provider = next(
        (
            p
            for p in yaml_content["providers"]["inference"]
            if p.get("provider_id") == provider_id
        ),
        None,
    )

    if existing_provider:
        logger.info(
            f"Provider '{provider_id}' already exists, skipping provider creation"
        )
    else:
        # Add new provider to inference providers
        new_provider = {
            "provider_id": provider_id,
            "provider_type": provider_type,
            "config": provider_config,
        }
        yaml_content["providers"]["inference"].append(new_provider)
        logger.info(f"Added provider '{provider_id}' to inference providers")

    if "models" not in yaml_content:
        yaml_content["models"] = []

    # Check if model with same model_id and provider_id already exists
    existing_model = next(
        (
            m
            for m in yaml_content["models"]
            if m.get("model_id") == model_id and m.get("provider_id") == provider_id
        ),
        None,
    )

    if existing_model:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model '{model_id}' with provider '{provider_id}' already exists",
        )

    # Add new model
    new_model = {
        "model_id": model_id,
        "provider_id": provider_id,
        "model_type": "llm",
        "metadata": metadata or {},
    }
    yaml_content["models"].append(new_model)
    logger.info(f"Added model '{model_id}' to configuration")

    return yaml_content


def patch_configmap(
    namespace: str, configmap_name: str, configmap: Any, yaml_content: dict
) -> None:
    """Patch ConfigMap with updated YAML configuration."""
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    core_v1 = k8s_client.CoreV1Api()

    updated_yaml = yaml.dump(yaml_content, default_flow_style=False)
    configmap.data["config.yaml"] = updated_yaml

    core_v1.patch_namespaced_config_map(
        name=configmap_name, namespace=namespace, body=configmap
    )
    logger.info(f"Successfully patched ConfigMap '{configmap_name}'")


def restart_deployment(
    namespace: str, deployment_name: str = "ai-virtual-agent"
) -> None:
    """Restart deployment using Kubernetes API."""
    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    apps_v1 = k8s_client.AppsV1Api()

    # Trigger rollout restart by updating annotation
    now = time.strftime("%Y%m%d-%H%M%S")
    body = {
        "spec": {
            "template": {
                "metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": now}}
            }
        }
    }

    apps_v1.patch_namespaced_deployment(
        name=deployment_name, namespace=namespace, body=body
    )
    logger.info(f"Successfully triggered restart for deployment '{deployment_name}'")
