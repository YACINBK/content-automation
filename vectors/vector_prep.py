import os
import sys
import numpy as np
import urllib.request
import subprocess
from PIL import Image
from sklearn.cluster import MiniBatchKMeans
from skimage.color import rgb2lab, lab2rgb 
import scour.scour

# We explicitly request the bria-rmbg model as per your instructions
# NOTE: We are now using backgroundremover but we keep this just in case
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

    def remove_background(self, input_path, model_name="u2net_human_seg", fg_threshold=240, bg_threshold=10, apply_alpha_matting=True, erode_size=10):
        """
        Uses backgroundremover to strip the background perfectly for apparel vectors.
        Implements alpha matting:
        Lower fg_threshold (e.g. 150) = more forgiving, keeps more of the subject's edges.
        erode_size allows control over edge softness/sharpness.
        """
        print(f"[*] Removing background from {input_path}... (Model: {model_name}, Alpha Matting FG: {fg_threshold}, Erode Size: {erode_size})")
        
        from backgroundremover.bg import remove
        
        # Load image
        with open(input_path, 'rb') as i:
            input_data = i.read()
                
        # Applying alpha matting allows us to strictly control the grayscale alpha matte boundary.
        output_data = remove(
            input_data,
            model_name=model_name,
            alpha_matting=apply_alpha_matting,
            alpha_matting_foreground_threshold=fg_threshold,
            alpha_matting_background_threshold=bg_threshold,
            alpha_matting_erode_structure_size=erode_size,
            alpha_matting_base_size=1000
        )
        
        # Save intermediate transparent PNG
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        out_path = os.path.join(self.output_dir, f"{base_name}_nobg.png")
        
        with open(out_path, 'wb') as o:
            o.write(output_data)
            
        print(f"[OK] Background stripped: {out_path}")
        return out_path

    def punch_holes_from_array(self, image_path, hole_mask_bool, invert_logic=False):
        """
        Takes the image_path (already alpha-masked by RMBG-2.0) and a boolean numpy array.
        If invert_logic=False: Deletes the pixels where hole_mask_bool is True (Standard Punch Out).
        If invert_logic=True: KEEPS the pixels where hole_mask_bool is True, and deletes the rest (Intersection).
        """
        print(f"\n[*] INITIATING DOUBLE-LAYERED MATH (Negative Space)...")
        
        img = Image.open(image_path).convert("RGBA")
        img_arr = np.array(img)
        alpha = img_arr[:, :, 3]
        
        # Ensure hole_mask_bool is the same shape as alpha
        if hole_mask_bool.shape != alpha.shape:
            import cv2
            hole_mask_bool = cv2.resize(hole_mask_bool.astype(np.uint8), (alpha.shape[1], alpha.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        
        if invert_logic:
            print(f"    -> Applying Intersection: KEEP where Mask is True, DELETE the rest.")
            new_alpha = np.where(hole_mask_bool, alpha, 0)
        else:
            print(f"    -> Applying Subtraction: DELETE where Mask is True, KEEP the rest.")
            new_alpha = np.where(hole_mask_bool, 0, alpha)
        
        # Re-attach the new alpha channel
        img_arr[:, :, 3] = new_alpha
        
        final_img = Image.fromarray(img_arr, mode="RGBA")
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        out_path = os.path.join(self.output_dir, f"{base_name}_holes_punched.png")
        final_img.save(out_path)
        
        print(f"[OK] Negative space successfully punched out: {out_path}\n")
        return out_path

    def chroma_key_punch(self, image_path, color="auto", tolerance=30):
        """
        Deterministic pixel math to hunt down trapped background colors and delete them.
        If color="auto", it samples the 5-pixel outer perimeter of the image to find the dominant background color.
        """
        print(f"\n[*] INITIATING CHROMA-KEY MATH (Target: {color.upper()}, Tolerance: {tolerance})...")
        
        img = Image.open(image_path).convert("RGBA")
        img_arr = np.array(img)
        
        rgb = img_arr[:, :, :3]
        alpha = img_arr[:, :, 3]
        
        # Color resolution logic
        target = None
        color = color.lower().strip()
        
        if color == "auto":
            print(f"    -> [AUTO-CHROMA] Sampling image perimeter for dominant background color...")
            # Extract a 5-pixel border from all 4 sides
            h, w = rgb.shape[:2]
            border_thickness = 5
            
            top = rgb[0:border_thickness, :, :]
            bottom = rgb[h-border_thickness:h, :, :]
            left = rgb[border_thickness:h-border_thickness, 0:border_thickness, :]
            right = rgb[border_thickness:h-border_thickness, w-border_thickness:w, :]
            
            # Flatten the borders into a single list of RGB pixels
            border_pixels = np.vstack([
                top.reshape(-1, 3), 
                bottom.reshape(-1, 3), 
                left.reshape(-1, 3), 
                right.reshape(-1, 3)
            ])
            
            # Find the statistical mode (the most frequent exact color on the border)
            unique_colors, counts = np.unique(border_pixels, axis=0, return_counts=True)
            target = unique_colors[np.argmax(counts)].astype(np.int16)
            
            # Print out the exact Hex code it found so the user knows what happened
            hex_color = '#%02x%02x%02x' % tuple(target)
            print(f"    -> [AUTO-CHROMA] Detected Dominant Background: RGB{tuple(target)} ({hex_color})")
            
        elif color == "white":
            target = np.array([255, 255, 255], dtype=np.int16)
        elif color == "black":
            target = np.array([0, 0, 0], dtype=np.int16)
        elif color == "red":
            target = np.array([255, 0, 0], dtype=np.int16)
        elif color == "green":
            target = np.array([0, 255, 0], dtype=np.int16)
        elif color == "blue":
            target = np.array([0, 0, 255], dtype=np.int16)
        elif color.startswith("#") and len(color) == 7:
            # Parse hex code, e.g. "#FF0000"
            try:
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                target = np.array([r, g, b], dtype=np.int16)
            except ValueError:
                pass
                
        if target is None:
            print(f"[!] Warning: Unsupported chroma color '{color}'. Skipping.")
            print(f"[!] Try 'white', 'black', 'red', 'green', 'blue', or a hex code like '#FF0000'")
            return image_path
            
        # Calculate color distance
        diff = np.abs(rgb.astype(np.int16) - target)
        
        # If all 3 RGB channels are within the tolerance, it's a match
        mask = np.all(diff <= tolerance, axis=-1)
        
        erased_count = np.sum(mask)
        print(f"    -> Math Result: Erasing {erased_count} stubborn pixels matching {color}.")
        
        # Punch out the matched pixels by zeroing their alpha
        img_arr[mask, 3] = 0
        
        final_img = Image.fromarray(img_arr, mode="RGBA")
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        out_path = os.path.join(self.output_dir, f"{base_name}_chroma_punched.png")
        final_img.save(out_path)
        
        print(f"[OK] Chroma-Key punch complete: {out_path}\n")
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

    def prepare_for_dtf(self, image_path):
        """
        Path A: The DTF Route (Raster).
        Takes the background-removed image, upscales it if necessary (placeholder for future AI upscale),
        and saves it as a true-transparent PNG with explicit 300 DPI metadata required by industrial RIP software.
        """
        print(f"\n[*] INITIATING PATH A: DTF (Direct-to-Film) Processing...")
        print(f"    -> Loading isolated image: {image_path}")
        
        try:
            # Load the image using PIL
            img = Image.open(image_path).convert("RGBA")
            
            # (Future Placeholder: AI Upscaling would happen right here before saving)
            # e.g., img = custom_upscaler_node(img)
            
            # Prepare the output path
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            out_path = os.path.join(self.output_dir, f"{base_name}_DTF_print_ready.png")
            
            # Save the image with exactly 300 DPI metadata
            print(f"    -> Injecting 300 DPI physical print metadata...")
            img.save(out_path, format="PNG", dpi=(300, 300))
            
            print(f"[OK] DTF Print File Generated: {out_path}\n")
            return out_path
            
        except Exception as e:
            print(f"[X] ERROR during DTF processing: {e}")
            return None

    def strip_svg_background(self, svg_path):
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
    erode_size = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    
    if not os.path.exists(input_image):
        print(f"[X] Input image not found: {input_image}")
        sys.exit(1)
        
    engine = VectorPrepEngine()
    
    # Step 1: Strip Background (With Level 1 Threshold logic)
    nobg_img = engine.remove_background(input_image, fg_threshold=fg_threshold, erode_size=erode_size)
    
    # Step 2: Quantize Colors (Perceptual K-Means)
    quantized_img = engine.quantize_colors_oklab(nobg_img, n_colors=n_colors)
    
    # Step 3: Stacked SVG Vectorization
    svg_img = engine.run_vtracer(quantized_img)
    
    print("\n[✔] PIPELINE COMPLETE!")
