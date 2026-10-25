import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from converters.registry import registry
from converters.base import ConversionOptions

opts = registry.get_target_options_for_source("docx")
print("Target options for DOCX:")
for opt in opts:
    print(f"  {opt.target_format.upper()}: enabled={opt.is_enabled}, reason='{opt.disabled_reason}'")

# Test DocxToPdfConverter directly
conv = registry.get_converter("docx", "pdf")
print("Converter for docx -> pdf:", conv)
res = conv.convert(
    Path("test_samples/sample_resume.docx"),
    ConversionOptions(custom_output_name="sample_resume_registry_test")
)
print("Conversion result success:", res.success)
print("Output files:", res.output_files)
if res.success:
    print("Output size:", res.output_files[0].stat().st_size)
else:
    print("Error:", res.error_message)
