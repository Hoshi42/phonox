#!/usr/bin/env python3
"""
LangGraph Fine-tuning Script for Vinyl Record Identification

This script tests and fine-tunes the LangGraph agent using sample images
from the docs/ directory to improve accuracy and fix common issues.
"""

import os
import sys
import base64
import json
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from backend.agent.graph import build_agent_graph
from backend.agent.state import VinylState
from backend.agent.vision import extract_vinyl_metadata

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample images in docs directory
SAMPLE_IMAGES = [
    "docs/R-367959-1348021211-7343.jpg",  # Sample 1
    "docs/R-376907-1622750570-9909.jpg",  # Sample 2  
    "docs/R-376907-1622750593-1566.jpg",  # Sample 3
    "docs/R-376907-1622750649-5281.jpg"   # Sample 4
]

# Expected results for validation (you can update these based on actual content)
EXPECTED_RESULTS = {
    "R-367959-1348021211-7343.jpg": {
        "artist": "Unknown",  # Update with actual expected values
        "title": "Unknown",
        "confidence_min": 0.5
    },
    "R-376907-1622750570-9909.jpg": {
        "artist": "Danzig",
        "title": "Danzig",
        "confidence_min": 0.7
    },
    "R-376907-1622750593-1566.jpg": {
        "artist": "Danzig",
        "title": "Danzig", 
        "confidence_min": 0.7
    },
    "R-376907-1622750649-5281.jpg": {
        "artist": "Danzig",
        "title": "Danzig",
        "confidence_min": 0.7
    }
}

def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")

def test_vision_extraction_only(image_path: str) -> dict:
    """Test just the vision extraction component."""
    logger.info(f"Testing vision extraction for: {image_path}")
    
    if not os.path.exists(image_path):
        logger.error(f"Image not found: {image_path}")
        return {}
    
    try:
        # Encode image
        image_base64 = encode_image_to_base64(image_path)
        
        # Test vision extraction directly
        result = extract_vinyl_metadata(
            image_base64=image_base64,
            image_format="jpeg",
            fallback_on_error=False
        )
        
        logger.info(f"Vision extraction result: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        logger.error(f"Vision extraction failed for {image_path}: {e}")
        return {}

def test_full_langgraph(image_path: str) -> dict:
    """Test the complete LangGraph workflow."""
    logger.info(f"Testing full LangGraph for: {image_path}")
    
    if not os.path.exists(image_path):
        logger.error(f"Image not found: {image_path}")
        return {}
    
    try:
        # Build the graph
        graph = build_agent_graph()
        
        # Prepare image data
        image_base64 = encode_image_to_base64(image_path)
        image_name = os.path.basename(image_path)
        
        # Create initial state
        initial_state: VinylState = {
            "images": [{
                "path": image_name,
                "content": image_base64,
                "content_type": "image/jpeg"
            }],
            "validation_passed": False,
            "image_features": {},
            "vision_extraction": {},
            "evidence_chain": [],
            "confidence": 0.0,
            "auto_commit": False,
            "needs_review": True,
        }
        
        # Run the graph
        config = {"configurable": {"thread_id": f"test_{image_name}"}}
        final_state = graph.invoke(initial_state, config=config)
        
        logger.info(f"LangGraph final state: {json.dumps({
            'validation_passed': final_state.get('validation_passed'),
            'vision_extraction': final_state.get('vision_extraction', {}),
            'confidence': final_state.get('confidence'),
            'auto_commit': final_state.get('auto_commit'),
            'needs_review': final_state.get('needs_review'),
            'error': final_state.get('error')
        }, indent=2, default=str)}")
        
        return final_state
        
    except Exception as e:
        logger.error(f"LangGraph test failed for {image_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

def validate_results(image_path: str, result: dict):
    """Validate the results against expected values."""
    image_name = os.path.basename(image_path)
    expected = EXPECTED_RESULTS.get(image_name, {})
    
    if not expected:
        logger.warning(f"No expected results defined for {image_name}")
        return
    
    vision_data = result.get('vision_extraction', {})
    
    # Check artist
    expected_artist = expected.get('artist')
    actual_artist = vision_data.get('artist')
    if expected_artist and actual_artist:
        if expected_artist.lower() in actual_artist.lower() or actual_artist.lower() in expected_artist.lower():
            logger.info(f"✓ Artist match: expected '{expected_artist}', got '{actual_artist}'")
        else:
            logger.warning(f"✗ Artist mismatch: expected '{expected_artist}', got '{actual_artist}'")
    
    # Check title
    expected_title = expected.get('title')
    actual_title = vision_data.get('title')
    if expected_title and actual_title:
        if expected_title.lower() in actual_title.lower() or actual_title.lower() in expected_title.lower():
            logger.info(f"✓ Title match: expected '{expected_title}', got '{actual_title}'")
        else:
            logger.warning(f"✗ Title mismatch: expected '{expected_title}', got '{actual_title}'")
    
    # Check confidence
    min_confidence = expected.get('confidence_min', 0.5)
    actual_confidence = result.get('confidence', 0.0)
    if actual_confidence >= min_confidence:
        logger.info(f"✓ Confidence acceptable: {actual_confidence:.2f} >= {min_confidence}")
    else:
        logger.warning(f"✗ Confidence too low: {actual_confidence:.2f} < {min_confidence}")

def run_comprehensive_test():
    """Run comprehensive tests on all sample images."""
    logger.info("="*80)
    logger.info("STARTING LANGGRAPH FINE-TUNING TESTS")
    logger.info("="*80)
    
    results = {}
    
    for image_path in SAMPLE_IMAGES:
        if not os.path.exists(image_path):
            logger.error(f"Sample image not found: {image_path}")
            continue
            
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTING: {os.path.basename(image_path)}")
        logger.info(f"{'='*60}")
        
        # Test 1: Vision extraction only
        logger.info("\n--- Test 1: Vision Extraction Only ---")
        vision_result = test_vision_extraction_only(image_path)
        
        # Test 2: Full LangGraph workflow
        logger.info("\n--- Test 2: Full LangGraph Workflow ---")
        langgraph_result = test_full_langgraph(image_path)
        
        # Store results
        results[os.path.basename(image_path)] = {
            'vision_only': vision_result,
            'full_langgraph': langgraph_result
        }
        
        # Validate results
        logger.info("\n--- Validation ---")
        validate_results(image_path, langgraph_result)
    
    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("SUMMARY")
    logger.info(f"{'='*80}")
    
    for image_name, test_results in results.items():
        logger.info(f"\n{image_name}:")
        
        vision_result = test_results.get('vision_only', {})
        if vision_result:
            logger.info(f"  Vision: {vision_result.get('artist', 'Unknown')} - {vision_result.get('title', 'Unknown')} (confidence: {vision_result.get('confidence', 0):.2f})")
        
        langgraph_result = test_results.get('full_langgraph', {})
        vision_extraction = langgraph_result.get('vision_extraction', {})
        if vision_extraction:
            logger.info(f"  LangGraph: {vision_extraction.get('artist', 'Unknown')} - {vision_extraction.get('title', 'Unknown')} (confidence: {langgraph_result.get('confidence', 0):.2f})")
        
        if langgraph_result.get('error'):
            logger.error(f"  Error: {langgraph_result['error']}")
    
    return results

def analyze_barcode_detection():
    """Specifically test barcode detection capabilities."""
    logger.info(f"\n{'='*60}")
    logger.info("BARCODE DETECTION ANALYSIS")
    logger.info(f"{'='*60}")
    
    for image_path in SAMPLE_IMAGES:
        if not os.path.exists(image_path):
            continue
            
        logger.info(f"\nAnalyzing barcodes in: {os.path.basename(image_path)}")
        
        try:
            image_base64 = encode_image_to_base64(image_path)
            result = extract_vinyl_metadata(image_base64, "jpeg", False)
            
            barcode = result.get('barcode')
            catalog_number = result.get('catalog_number')
            
            logger.info(f"  Barcode: {barcode if barcode else 'Not detected'}")
            logger.info(f"  Catalog Number: {catalog_number if catalog_number else 'Not detected'}")
            
        except Exception as e:
            logger.error(f"  Error analyzing barcodes: {e}")

if __name__ == "__main__":
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Run comprehensive tests
    results = run_comprehensive_test()
    
    # Run barcode-specific analysis
    analyze_barcode_detection()
    
    logger.info(f"\n{'='*80}")
    logger.info("FINE-TUNING COMPLETE")
    logger.info(f"{'='*80}")