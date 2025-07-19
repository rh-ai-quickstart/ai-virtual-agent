#!/usr/bin/env python3
"""
Quick test script to debug template loading
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.template_service import template_service

def test_template_loading():
    print("=== Testing Template Loading ===")
    print(f"Templates directory: {template_service.templates_dir}")
    print(f"Directory exists: {template_service.templates_dir.exists()}")
    
    # List YAML files
    yaml_files = list(template_service.templates_dir.glob("*.yaml"))
    print(f"Found {len(yaml_files)} YAML files:")
    for f in yaml_files:
        print(f"  - {f.name}")
    
    # Try to load templates
    try:
        templates = template_service.load_templates(force_reload=True)
        print(f"Successfully loaded {len(templates)} templates")
        for t in templates:
            print(f"  - {t.name} ({t.id}) - {len(t.agents)} agents")
    except Exception as e:
        print(f"Error loading templates: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_template_loading() 