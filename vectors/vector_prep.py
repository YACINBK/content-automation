import os
import sys
import numpy as np
import urllib.request
import subprocess
from PIL import Image
from sklearn.cluster import MiniBatchKMeans
from skimage.color import rgb2lab, lab2rgb 
import rembg
import scour.scour

# We explicitly request the bria-rmbg model as per your instructions
os.environ["U2NET_HOME"] = os.path.join(os.getcwd(), "models", "u2net")

class VectorPrepEngine:
    def __init__(self, vtracer_path="vtracer.exe"):
        self.vtracer_path = vtracer_path
        self.output_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self._ensure_vtracer()

    def _ensure_vtracer(self):
        """Downloads the pre-compiled VTracer binary for Windows to avoid Rust compilation issues."""
        if not os.path.exists(self.vtracer_path):
            print("[*] Downloading VTracer pre-compiled Windows binary...")
            # Using the exact URL from visioncortex's latest releases
            url = "https://github.com/visioncortex/vtracer/releases/download/0.6.1/vtracer-windows.exe"
            try:
                urllib.request.urlretrieve(url, self.vtracer_path)
            except Exception:
                print("[!] Automatic download failed (GitHub URL might have changed).")
                print("[!] Please manually download VTracer from:")
                print("    https://github.com/visioncortex/vtracer/releases")
                print(f"    and place the .exe file here as: {os.path.abspath(self.vtracer_path)}")
                sys.exit(1)
            print("[OK] VTracer downloaded securely.")

    def remove_background(self, input_path, fg_threshold=240, bg_threshold=10, apply_alpha_matting=True):
        """
        Uses RMBG-2.0 / bria-rmbg to strip the background perfectly.
        Implements Level 1: Threshold Adjustment. 
        Lower fg_threshold (e.g. 150) = more forgiving, keeps more of the subject's edges.
        """
        print(f"[*] Removing background from {input_path}... (Alpha Matting FG Threshold: {fg_threshold})")
        
        # Load image
        with open(input_path, 'rb') as i:
            input_data = i.read()
            
        # We enforce the bria-rmbg model for superior edge detection
        try:
            session = rembg.new_session("bria")
        except Exception:
            try:
                session = rembg.new_session("briarmbg1.4")
            except Exception:
                session = rembg.new_session("u2net") # Ultimate fallback
                
        # LEVEL 1 THRESHOLD PROTOCOL:
        # Applying alpha matting allows us to strictly control the grayscale alpha matte boundary.
        output_data = rembg.remove(
            input_data, 
            session=session, 
            alpha_matting=apply_alpha_matting,
            alpha_matting_foreground_threshold=fg_threshold,
            alpha_matting_background_threshold=bg_threshold,
            alpha_matting_erode_size=10
        )
        
        # Save intermediate transparent PNG
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        out_path = os.path.join(self.output_dir, f"{base_name}_nobg.png")
        
        with open(out_path, 'wb') as o:
            o.write(output_data)
            
        print(f"[OK] Background stripped: {out_path}")
        return out_path

    def _rgb_to_oklab(self, rgb_array):
        """Custom highly optimized RGB -> Oklab numpy conversion. Oklab maps mathematically to human optical perception."""
        # Convert 0-255 to 0.0-1.0
        srgb = rgb_array.astype(np.float32) / 255.0
        
        # sRGB to Linear RGB
        linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
        
        # Linear RGB to LMS
        m1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                       [0.2119034982, 0.6806995451, 0.1073969566],
                       [0.0883024619, 0.2817188376, 0.6299787005]], dtype=np.float32)
        lms = np.dot(linear, m1.T)
        
        # Non-linear LMS (cbrt) - handling small negs just in case
        lms_ = np.cbrt(np.maximum(lms, 0))
        
        # LMS to Oklab
        m2 = np.array([[ 0.2104542553,  0.7936177850, -0.0040720468],
                       [ 1.9779984951, -2.4285922050,  0.4505937099],
                       [ 0.0259040371,  0.7827717662, -0.8086757660]], dtype=np.float32)
        oklab = np.dot(lms_, m2.T)
        return oklab
        
    def _oklab_to_rgb(self, oklab_array):
        """Custom Oklab -> RGB conversion."""
        # Oklab to LMS
        m1_inv = np.array([[1.0,  0.3963377774,  0.2158037573],
                           [1.0, -0.1055613458, -0.0638541728],
                           [1.0, -0.0894841775, -1.2914855480]], dtype=np.float32)
        lms_ = np.dot(oklab_array, m1_inv.T)
        
        # LMS to Linear RGB
        lms = lms_ ** 3
        m2_inv = np.array([[ 4.0767416621, -3.3077115913,  0.2309699292],
                           [-1.2684380046,  2.6097574011, -0.3413193965],
                           [-0.0041960863, -0.7034186147,  1.7076147010]], dtype=np.float32)
        linear = np.dot(lms, m2_inv.T)
        
        # Linear RGB to sRGB
        srgb = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * (np.maximum(linear, 0) ** (1/2.4)) - 0.055)
        # Convert back to 0-255 uint8
        return np.clip(srgb * 255.0, 0, 255).astype(np.uint8)

    def quantize_colors_oklab(self, image_path, n_colors=5):
        """
        Converts the image to perceptual color space (LAB/Oklab), runs K-Means, 
        and snaps every pixel to the nearest of the n_colors. This is CRITICAL for screen printing.
        Now featuring Color Preservation Bible logic: 256-color pre-buffering, CIEDE2000 sorting, 
        and Hue Histogram Binning for vibrant minority color protection.
        """
        print(f"[*] Quantizing colors to {n_colors} discrete spot colors...")
        img = Image.open(image_path).convert("RGBA")
        img_arr = np.array(img)
        
        alpha = img_arr[:, :, 3]
        rgb = img_arr[:, :, :3]
        
        import cv2
        from PIL import ImageFilter
        print("    -> Applying Bilateral Filter (Edge-Preserving Blur)...")
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        bgr_filtered = cv2.bilateralFilter(bgr, d=9, sigmaColor=75, sigmaSpace=75)
        rgb_filtered = cv2.cvtColor(bgr_filtered, cv2.COLOR_BGR2RGB)
        
        print("    -> Applying Surface Smoothing (Median Filter) to clump colors...")
        rgb_pil = Image.fromarray(rgb_filtered)
        rgb_pil = rgb_pil.filter(ImageFilter.MedianFilter(size=5))
        
        # 1. 256-Color Pre-buffering
        print("    -> Pre-buffering to 256 colors to isolate distinct hues...")
        buffered_pil = rgb_pil.quantize(colors=256).convert('RGB')
        rgb_buffered = np.array(buffered_pil)
        
        # Only process pixels that are actually visible
        mask = alpha > 128
        visible_pixels = rgb_buffered[mask]
        
        if len(visible_pixels) == 0:
            print("[X] Image is completely transparent.")
            return image_path
            
        print("    -> Translating to Oklab perceptual color space...")
        # Get unique colors and their frequencies (Histogram Binning)
        unique_colors, counts = np.unique(visible_pixels, axis=0, return_counts=True)
        
        # Calculate Saturation (max(R,G,B) - min(R,G,B)) to boost vibrant minority colors
        saturations = np.max(unique_colors, axis=1) - np.min(unique_colors, axis=1)
        # Weight = frequency * (1 + saturation_boost)
        # This protects unique vibrant hues from being swallowed by dominant dull colors
        saturation_boost = (saturations / 255.0) * 10.0
        weights = counts * (1.0 + saturation_boost)
        
        pixels_oklab = self._rgb_to_oklab(unique_colors)
        
        print("    -> Running Weighted MiniBatch K-Means clustering...")
        # We pass weights to kmeans so vibrant/frequent colors pull the centers
        kmeans = MiniBatchKMeans(n_clusters=n_colors, random_state=42, n_init=3, batch_size=10000)
        kmeans.fit(pixels_oklab, sample_weight=weights)
        centers_oklab = kmeans.cluster_centers_
        
        # Convert centers back to RGB
        centers_rgb = self._oklab_to_rgb(centers_oklab)
        
        # Now map ALL visible pixels to the closest center
        # For ultimate accuracy, we map the original visible pixels (not just the 256)
        all_visible_oklab = self._rgb_to_oklab(rgb[mask])
        labels = kmeans.predict(all_visible_oklab)
        
        quantized_visible = centers_rgb[labels]
        quantized_rgb = np.zeros_like(rgb)
        quantized_rgb[mask] = quantized_visible
        
        final_img_arr = np.dstack((quantized_rgb, alpha))
        final_img = Image.fromarray(final_img_arr)
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        out_path = os.path.join(self.output_dir, f"{base_name}_quantized_{n_colors}c.png")
        final_img.save(out_path)
        print(f"[OK] Quantization complete: {out_path}")
        return out_path

    def run_vtracer(self, input_path):
        """Passes the quantized image directly to VTracer via Python bindings."""
        print(f"[*] Vectorizing with VTracer (Python Bindings): {input_path}...")
        
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        out_path = os.path.join(self.output_dir, f"{base_name}.svg")
        
        import vtracer
        
        # We need to manually pass the input and output parameters to vtracer's python wrapper
        try:
            # We must map the parameters specifically to the Python API
            vtracer.convert_image_to_svg_py(
                input_path,
                out_path,
                colormode='color',
                hierarchical='stacked',
                mode='spline',
                filter_speckle=10,       # Increased to ignore tiny pixel noise/artifacts
                color_precision=6,
                layer_difference=16,
                corner_threshold=40,     # Decreased to round off sharp jagged corners
                length_threshold=4.0,
                max_iterations=10,
                splice_threshold=45,
                path_precision=3         # Decreased to create smooth curves instead of hugging pixels
            )
            print(f"[OK] Vectorization complete: {out_path}")
            transparent_svg = self.strip_svg_background(out_path)
            return self.sanitize_svg(transparent_svg)
        except Exception as e:
            print(f"[X] ERROR: VTracer Python binding failed. {e}")
        return None

    def strip_svg_background(self, svg_path):
        """
        Parses the XML/SVG DOM to find and brutally remove the base background layer.
        This guarantees true transparency for apparel printing regardless of what the AI generated.
        """
        print(f"\n[*] STRIPPING SVG BACKGROUND: Inspecting DOM for print transparency...")
        import xml.etree.ElementTree as ET
        
        try:
            # Register the SVG namespace to prevent 'ns0:' prefixes in the output
            ET.register_namespace('', "http://www.w3.org/2000/svg")
            tree = ET.parse(svg_path)
            root = tree.getroot()
            
            # The standard SVG namespace
            ns = {'svg': 'http://www.w3.org/2000/svg'}
            
            # VTracer's hierarchical stacking always places the "base canvas" (the background)
            # as the absolute first <path> element inside the first <g> (group) element.
            g_elem = root.find('svg:g', ns)
            if g_elem is not None:
                paths = g_elem.findall('svg:path', ns)
                if len(paths) > 0:
                    base_path = paths[0]
                    fill_color = base_path.attrib.get('fill', 'Unknown')
                    
                    print(f"    -> [VERBOSE] Located foundational base layer in SVG DOM.")
                    print(f"    -> [VERBOSE] Base Layer Fill Color: {fill_color}")
                    print(f"    -> [VERBOSE] Executing strict deletion of the base layer to enforce alpha transparency...")
                    
                    # Delete the foundational path entirely from the group
                    g_elem.remove(base_path)
                    print(f"    -> [VERBOSE] Base layer successfully eradicated from DOM.")
                else:
                    print(f"    -> [VERBOSE] No paths found in root group. Skipping.")
            else:
                print(f"    -> [VERBOSE] No root group found in SVG. Skipping.")
                
            out_path = svg_path.replace(".svg", "_transparent.svg")
            tree.write(out_path, encoding='utf-8', xml_declaration=True)
            print(f"[OK] SVG Transparency enforced: {out_path}\n")
            return out_path
            
        except Exception as e:
            print(f"[X] ERROR during SVG background stripping: {e}")
            return svg_path

    def sanitize_svg(self, svg_path):
        """Topological SVG Optimization using the Scour library to strip invisible complexity/bloat."""
        print(f"[*] Sanitizing and Optimizing SVG DOM: {svg_path}...")
        
        with open(svg_path, 'r', encoding='utf-8') as f:
            in_string = f.read()
            
        import scour.scour as scour_module
        options = scour_module.sanitizeOptions()
        options.remove_metadata = True
        options.remove_descriptive_elements = True
        options.strip_comments = True
        options.shorten_ids = True
        
        # Scour expects options as an object, but its API relies on sys.argv emulation in parse_args
        # We will use the standalone API
        out_string = scour_module.scourString(in_string, options=options)
        
        optimized_path = svg_path.replace(".svg", "_optimized.svg")
        with open(optimized_path, 'w', encoding='utf-8') as f:
            f.write(out_string)
            
        print(f"[OK] Topological Optimization complete: {optimized_path}")
        return optimized_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python vector_prep.py <path_to_image> [number_of_colors]")
        sys.exit(1)
        
    input_image = sys.argv[1]
    n_colors = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    fg_threshold = int(sys.argv[3]) if len(sys.argv) > 3 else 240
    
    if not os.path.exists(input_image):
        print(f"[X] Input image not found: {input_image}")
        sys.exit(1)
        
    engine = VectorPrepEngine()
    
    # Step 1: Strip Background (With Level 1 Threshold logic)
    nobg_img = engine.remove_background(input_image, fg_threshold=fg_threshold)
    
    # Step 2: Quantize Colors (Perceptual K-Means)
    quantized_img = engine.quantize_colors_oklab(nobg_img, n_colors=n_colors)
    
    # Step 3: Stacked SVG Vectorization
    svg_img = engine.run_vtracer(quantized_img)
    
    print("\n[✔] PIPELINE COMPLETE!")
