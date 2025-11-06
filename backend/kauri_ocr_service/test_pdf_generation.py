#!/usr/bin/env python
"""
Test script for PDF generation functionality
Tests the PDF generator service with a sample document
"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_generator import pdf_generator_service
from app.core.config import settings


async def test_pdf_generation():
    """Test PDF generation with a sample file"""
    print("=" * 70)
    print("Testing PDF Generator Service")
    print("=" * 70)

    # Check if a test PDF exists
    test_pdf = Path("test_input.pdf")

    if not test_pdf.exists():
        print("\n❌ Error: test_input.pdf not found in current directory")
        print("   Please place a test PDF file named 'test_input.pdf' here")
        return False

    print(f"\n✅ Found test input: {test_pdf}")
    print(f"   File size: {test_pdf.stat().st_size:,} bytes")

    # Test 1: Generate searchable PDF
    print("\n" + "=" * 70)
    print("TEST 1: Generate Searchable PDF")
    print("=" * 70)

    result = await pdf_generator_service.generate_searchable_pdf(
        input_pdf_path=str(test_pdf),
        output_filename="test_searchable.pdf"
    )

    if result['success']:
        print(f"✅ Success!")
        print(f"   Output: {result['output_filename']}")
        print(f"   Path: {result['output_path']}")
        print(f"   Size: {result['file_size']:,} bytes")
        print(f"   Message: {result['message']}")

        # Check if file exists
        output_path = Path(result['output_path'])
        if output_path.exists():
            print(f"✅ Output file verified on disk")

            # Calculate size reduction/increase
            original_size = test_pdf.stat().st_size
            new_size = output_path.stat().st_size
            diff_percent = ((new_size - original_size) / original_size) * 100

            if diff_percent > 0:
                print(f"   Size increased by {diff_percent:.1f}%")
            else:
                print(f"   Size reduced by {abs(diff_percent):.1f}%")
        else:
            print(f"❌ Output file not found on disk")
            return False
    else:
        print(f"❌ Failed!")
        print(f"   Error: {result.get('error')}")
        return False

    # Test 2: Optimize PDF
    print("\n" + "=" * 70)
    print("TEST 2: Optimize PDF")
    print("=" * 70)

    optimize_result = await pdf_generator_service.optimize_pdf(
        input_pdf_path=str(test_pdf),
        output_filename="test_optimized.pdf",
        optimization_level=2
    )

    if optimize_result['success']:
        print(f"✅ Success!")
        print(f"   Original: {optimize_result['original_size']:,} bytes")
        print(f"   Optimized: {optimize_result['optimized_size']:,} bytes")
        print(f"   Reduction: {optimize_result['reduction_percent']:.1f}%")
    else:
        print(f"⚠️  Optimization failed (this is optional)")
        print(f"   Error: {optimize_result.get('error')}")

    # Test 3: Service methods
    print("\n" + "=" * 70)
    print("TEST 3: Service Methods")
    print("=" * 70)

    # Check file exists
    if pdf_generator_service.file_exists("test_searchable.pdf"):
        print("✅ file_exists() works correctly")
    else:
        print("❌ file_exists() returned False for existing file")
        return False

    # Get output path
    output_path = pdf_generator_service.get_output_path("test_searchable.pdf")
    print(f"✅ get_output_path() returns: {output_path}")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)

    print("\n📁 Output files location:")
    print(f"   {pdf_generator_service.output_dir}")

    return True


async def test_image_to_pdf():
    """Test creating PDF from images"""
    print("\n" + "=" * 70)
    print("TEST 4: Generate PDF from Images (Optional)")
    print("=" * 70)

    # Look for test images
    image_extensions = ['.png', '.jpg', '.jpeg']
    test_images = []

    for ext in image_extensions:
        test_images.extend(Path(".").glob(f"*{ext}"))

    if not test_images:
        print("⚠️  No test images found (optional test skipped)")
        return

    print(f"✅ Found {len(test_images)} test image(s)")

    # Use first 3 images max
    test_images = [str(img) for img in test_images[:3]]

    result = await pdf_generator_service.generate_pdf_from_images(
        image_paths=test_images,
        output_filename="test_from_images.pdf",
        apply_ocr=True
    )

    if result['success']:
        print(f"✅ PDF created from images!")
        print(f"   Output: {result['output_filename']}")
        print(f"   Size: {result['file_size']:,} bytes")
    else:
        print(f"❌ Failed to create PDF from images")
        print(f"   Error: {result.get('error')}")


def main():
    """Main test runner"""
    print("\n🔧 KAURI OCR Service - PDF Generator Test")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"OCR Languages: {', '.join(settings.ocr_languages)}")

    try:
        success = asyncio.run(test_pdf_generation())

        # Optional: Test image to PDF
        asyncio.run(test_image_to_pdf())

        if success:
            print("\n✅ PDF generation is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
