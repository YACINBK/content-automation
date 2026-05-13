import os
import gc
import torch
import numpy as np
from PIL import Image
import cv2

# We will dynamically import heavy libraries to save memory until the exact moment they are needed
# import transformers

class SemanticVectorizer:
    def __init__(self, device="cuda" if torch.cuda.is_available() else "cpu"):
        self.device = device
        self.output_dir = os.path.join(os.getcwd(), "outputs", "semantic_layers")
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[*] Semantic Vectorizer Initialized. Target Device: {self.device}")
        print(f"[*] 8GB VRAM Constraint Active: Strict Sequential Loading Enabled.")

    def _flush_vram(self):
        """Aggressively purges the GPU memory to prevent PyTorch OOM crashes."""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def step1_florence_dense_captioning(self, image_path):
        """
        Loads Florence-2 to find and name all physical objects in the image.
        Returns a list of dictionaries containing labels and bounding boxes.
        """
        print("\n" + "="*50)
        print("🧠 STEP 1: FLORENCE-2 COGNITIVE LABELING")
        print("="*50)
        
        from transformers import AutoProcessor, AutoModelForCausalLM
        
        model_id = "microsoft/Florence-2-large"
        print(f"[*] Loading {model_id} into VRAM...")
        
        # Load model with strict memory management
        processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True, torch_dtype=torch.float16).to(self.device)
        
        image = Image.open(image_path).convert("RGB")
        
        # <DENSE_REGION_CAPTION> forces the model to find objects and give them specific names
        prompt = "<DENSE_REGION_CAPTION>"
        inputs = processor(text=prompt, images=image, return_tensors="pt").to(self.device, torch.float16)
        
        print(f"[*] Analyzing image semantics...")
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            do_sample=False,
            num_beams=3
        )
        
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = processor.post_process_generation(generated_text, task=prompt, image_size=(image.width, image.height))
        
        results = parsed_answer[prompt]
        
        # Clean up tags to make them valid SVG IDs (e.g. "a mother lion" -> "mother_lion")
        cleaned_results = []
        for label, box in zip(results['labels'], results['bboxes']):
            safe_label = label.lower().replace(" ", "_").replace("a_", "").replace("an_", "").strip("_")
            # Florence returns [x1, y1, x2, y2]
            cleaned_results.append({
                "label": safe_label,
                "box": box
            })
            
        print(f"[✔] Found {len(cleaned_results)} discrete semantic layers.")
        
        # AGGRESSIVE VRAM FLUSH
        print(f"[*] Purging Florence-2 from VRAM...")
        del model
        del processor
        del inputs
        del generated_ids
        self._flush_vram()
        
        return image, cleaned_results

    def step2_sam2_segmentation(self, image, florence_data):
        """
        Loads SAM 2. Takes the bounding boxes from Florence-2 and creates pixel-perfect masks.
        """
        print("\n" + "="*50)
        print("🔪 STEP 2: SAM 2 SEMANTIC SEGMENTATION")
        print("="*50)
        
        from transformers import AutoProcessor, AutoModelForMaskGeneration
        
        # We reuse the exact same SAM model and framework as smart_extractor.py to avoid 
        # downloading duplicate weights or causing library conflicts.
        sam_id = "facebook/sam-vit-base"
        print(f"[*] Loading {sam_id} into VRAM...")
        
        sam_processor = AutoProcessor.from_pretrained(sam_id)
        sam_model = AutoModelForMaskGeneration.from_pretrained(sam_id).to(self.device)
        
        # Prepare PIL image
        image_pil = image.copy()
        
        layer_masks = {}
        
        print(f"[*] Slicing {len(florence_data)} semantic objects...")
        for item in florence_data:
            label = item["label"]
            # Florence box format: [xmin, ymin, xmax, ymax]
            box = item["box"]
            
            # Predict mask using the Florence bounding box as a prompt
            # SAM processor expects boxes as a list of lists of lists: [[[xmin, ymin, xmax, ymax]]]
            input_boxes = [[box]]
            
            sam_inputs = sam_processor(images=image_pil, input_boxes=input_boxes, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                sam_outputs = sam_model(**sam_inputs)
                
            # SAM returns multiple masks. We take the highest quality one (index 0)
            masks = sam_processor.image_processor.post_process_masks(
                sam_outputs.pred_masks.cpu(),
                sam_inputs["original_sizes"].cpu(),
                sam_inputs["reshaped_input_sizes"].cpu()
            )[0]
            
            # masks shape: (1, 3, H, W) for single box
            best_mask = masks[0, 0, :, :].numpy() > 0.5
            
            # Handle duplicates (e.g. two "cloudy_sky" objects)
            unique_label = label
            counter = 1
            while unique_label in layer_masks:
                unique_label = f"{label}_{counter}"
                counter += 1
                
            layer_masks[unique_label] = best_mask
            print(f"    -> Extracted: <g id='{unique_label}'>")

        # AGGRESSIVE VRAM FLUSH
        print(f"[*] Purging SAM from VRAM...")
        del sam_model
        del sam_processor
        del sam_inputs
        del sam_outputs
        self._flush_vram()
        
        return layer_masks

    def step3_halftone_and_prepress(self, image, layer_masks):
        """
        Converts soft masks into true digital halftones (100% opacity binary dots) and applies trapping.
        Since we are doing apparel printing, there can be NO soft pixels.
        Returns a dictionary of paths to the processed raster layers ready for vtracer.
        """
        print("\n" + "="*50)
        print("🖨️ STEP 3: DIGITAL HALFTONING & PRE-PRESS TRAPPING")
        print("="*50)
        
        img_arr = np.array(image)
        h, w = img_arr.shape[:2]
        processed_paths = {}
        
        # We will use an ordered dither matrix (Bayer matrix) for reliable halftoning
        # 4x4 matrix mapped to 0-255
        bayer_matrix = np.array([
            [ 0,  8,  2, 10],
            [12,  4, 14,  6],
            [ 3, 11,  1,  9],
            [15,  7, 13,  5]
        ]) * 16
        
        # Tile the matrix to cover the entire image
        dither_map = np.tile(bayer_matrix, (h // 4 + 1, w // 4 + 1))[:h, :w]
        
        for label, bool_mask in layer_masks.items():
            # For soft alpha, we would normally use the continuous mask output from SAM 2.
            # But SAM 2 gives us a boolean mask. To simulate realistic edges, we apply a slight 
            # gaussian blur to the mask, then dither that blur to create halftone dots at the edge.
            
            mask_uint8 = (bool_mask.astype(np.uint8) * 255)
            
            # Trapping: Dilate the mask by 1 pixel (~0.1mm) to ensure it overlaps beneath neighboring layers slightly
            kernel = np.ones((3,3), np.uint8)
            trapped_mask = cv2.dilate(mask_uint8, kernel, iterations=1)
            
            # Create soft edge for halftoning
            soft_edge_mask = cv2.GaussianBlur(trapped_mask, (5,5), 0)
            
            # Apply Digital Halftone Logic
            # If the soft alpha > dither map value, it becomes solid (255), else it becomes empty (0)
            halftoned_mask = np.where(soft_edge_mask > dither_map, 255, 0).astype(np.uint8)
            
            # Create final 100% opacity layer (RGB + Halftoned Alpha)
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            rgba[:, :, :3] = img_arr
            rgba[:, :, 3] = halftoned_mask
            
            out_path = os.path.join(self.output_dir, f"{label}_halftoned.png")
            Image.fromarray(rgba).save(out_path)
            processed_paths[label] = out_path
            
            print(f"    -> Halftoned & Trapped: {out_path}")
            
        return processed_paths

    def step4_vtracer_stacking(self, processed_paths, out_svg_path):
        """
        Uses vtracer to trace each halftoned layer independently.
        Then injects them all into a single master SVG, grouping them with their semantic IDs.
        """
        print("\n" + "="*50)
        print("📐 STEP 4: SEMANTIC VECTORIZATION & SVG STACKING")
        print("="*50)
        
        import vtracer
        import xml.etree.ElementTree as ET
        
        # Register SVG namespace to prevent 'ns0:' prefixes
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        
        master_svg_root = None
        
        for label, img_path in processed_paths.items():
            print(f"    -> Tracing <g id='{label}'>...")
            temp_svg_path = os.path.join(self.output_dir, f"temp_{label}.svg")
            
            try:
                # We use strict parameters to ensure the halftoned dots are traced accurately
                vtracer.convert_image_to_svg_py(
                    img_path,
                    temp_svg_path,
                    colormode='color',
                    hierarchical='stacked',
                    mode='spline',
                    filter_speckle=1,       # MUST be very low to capture halftone dots
                    color_precision=6,
                    layer_difference=16,
                    corner_threshold=45,
                    length_threshold=3.5,
                    max_iterations=10,
                    splice_threshold=45,
                    path_precision=4
                )
                
                # Parse the generated SVG
                tree = ET.parse(temp_svg_path)
                root = tree.getroot()
                
                # Initialize master SVG using the attributes of the first traced SVG
                if master_svg_root is None:
                    master_svg_root = ET.Element("svg", root.attrib)
                
                # Create a group for this semantic layer
                group = ET.Element("g", attrib={"id": label})
                
                # Move all paths from the traced SVG into our semantic group
                # VTracer outputs paths inside <svg>. We just grab all elements inside.
                for child in list(root):
                    group.append(child)
                    
                master_svg_root.append(group)
                
                # Cleanup temp file
                os.remove(temp_svg_path)
                
            except Exception as e:
                print(f"[X] ERROR tracing {label}: {e}")
                
        if master_svg_root is not None:
            master_tree = ET.ElementTree(master_svg_root)
            master_tree.write(out_svg_path, encoding="utf-8", xml_declaration=True)
            print(f"\n[✔] SUCCESS: Master Semantic SVG saved to: {out_svg_path}")
        else:
            print(f"\n[X] FAILED to generate Master SVG.")

    def execute_cognitive_core(self, image_path):
        """Runs the complete VRAM-safe sequential loading process."""
        image, florence_data = self.step1_florence_dense_captioning(image_path)
        layer_masks = self.step2_sam2_segmentation(image, florence_data)
        
        # Save debug masks so the user can verify the AI's "understanding"
        final_svg = None
        if layer_masks:
            print("\n[*] Saving cognitive debug masks...")
            img_arr = np.array(image)
            for label, mask in layer_masks.items():
                # Create an RGBA image where the mask is visible
                rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
                
                # Create an alpha array of the same 1D shape as img_arr[mask]
                num_pixels = np.sum(mask)
                alpha_channel = np.full((num_pixels, 1), 255, dtype=np.uint8)
                
                # Combine RGB pixels with the Alpha pixels
                rgba[mask] = np.concatenate([img_arr[mask], alpha_channel], axis=-1)
                
                out_path = os.path.join(self.output_dir, f"{label}_debug.png")
                Image.fromarray(rgba).save(out_path)
            
            # Phase 3 & 4
            processed_paths = self.step3_halftone_and_prepress(image, layer_masks)
            
            final_svg = os.path.join(self.output_dir, "FINAL_SEMANTIC_VECTOR.svg")
            self.step4_vtracer_stacking(processed_paths, final_svg)
            
        return final_svg

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        engine = SemanticVectorizer()
        engine.execute_cognitive_core(sys.argv[1])
    else:
        print("Usage: python semantic_vectorizer.py <path_to_image>")
