import os
import gc
import time
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
from transformers import AutoModelForMaskGeneration

class SmartExtractor:
    def __init__(self, output_dir="outputs"):
        self.output_dir = os.path.join(os.getcwd(), output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def free_vram(self):
        """Strict VRAM management protocol to ensure 8GB RTX 4060 safety."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
        gc.collect()
        time.sleep(2)

    def extract_subject(self, image_path, text_prompt, box_threshold=0.3, text_threshold=0.3):
        """
        LEVEL 2 SMART PROTOCOL: Grounded SAM 2
        1. Grounding DINO finds bounding boxes based on the text prompt.
        2. SAM 2 generates pixel-perfect masks for those boxes.
        3. Aggressive VRAM flushing after each step.
        """
        print(f"\n" + "="*50)
        print(f"🎯 LEVEL 2 SMART EXTRACTION: GROUNDED SAM 2")
        print(f"[*] Target Subject: '{text_prompt}'")
        print(f"[*] Hardware Target: {self.device.upper()}")
        print("="*50)

        # Ensure VRAM is empty before we start
        self.free_vram()

        image = Image.open(image_path).convert("RGB")
        
        # ---------------------------------------------------------
        # PHASE 1: GROUNDING DINO (Text to Bounding Box)
        # ---------------------------------------------------------
        print("[*] PHASE 1/3: Loading Grounding DINO to locate objects...")
        dino_id = "IDEA-Research/grounding-dino-tiny"
        dino_processor = AutoProcessor.from_pretrained(dino_id)
        dino_model = AutoModelForZeroShotObjectDetection.from_pretrained(dino_id).to(self.device)

        print(f"    -> Analyzing image for: '{text_prompt}'")
        # Grounding DINO requires a period at the end of the prompt
        dino_text = text_prompt if text_prompt.endswith(".") else text_prompt + "."
        
        inputs = dino_processor(images=image, text=dino_text, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = dino_model(**inputs)

        results = dino_processor.post_process_grounded_object_detection(
            outputs,
            inputs.input_ids,
            box_threshold=box_threshold,
            text_threshold=text_threshold,
            target_sizes=[image.size[::-1]]
        )[0]

        boxes = results["boxes"]
        scores = results["scores"]
        labels = results["labels"]
        
        print(f"[OK] Found {len(boxes)} matching bounding box(es).")
        
        # Purge DINO from VRAM immediately
        del dino_model
        del dino_processor
        del inputs
        del outputs
        self.free_vram()

        if len(boxes) == 0:
            print("[!] WARNING: Grounding DINO found no matches. Falling back to original image.")
            return image_path

        # ---------------------------------------------------------
        # PHASE 2: SAM 2 (Bounding Box to Pixel Mask)
        # ---------------------------------------------------------
        print("[*] PHASE 2/3: Loading SAM to generate pixel-perfect masks...")
        # Using Facebook's standard SAM architecture accessible natively via transformers
        sam_id = "facebook/sam-vit-base"
        sam_processor = AutoProcessor.from_pretrained(sam_id)
        sam_model = AutoModelForMaskGeneration.from_pretrained(sam_id).to(self.device)

        # Prepare boxes for SAM (List of lists format)
        input_boxes = [boxes.cpu().numpy().tolist()]
        
        sam_inputs = sam_processor(images=image, input_boxes=input_boxes, return_tensors="pt").to(self.device)
        with torch.no_grad():
            sam_outputs = sam_model(**sam_inputs)

        # SAM returns shape (batch_size, num_boxes, num_masks, H, W)
        masks = sam_processor.image_processor.post_process_masks(
            sam_outputs.pred_masks.cpu(),
            sam_inputs["original_sizes"].cpu(),
            sam_inputs["reshaped_input_sizes"].cpu()
        )[0]
        
        # Purge SAM from VRAM immediately
        del sam_model
        del sam_processor
        del sam_inputs
        del sam_outputs
        self.free_vram()

        # ---------------------------------------------------------
        # PHASE 3: COMPOSITING HYBRID MASK (The Dilation Trick)
        # ---------------------------------------------------------
        print("[*] PHASE 3/3: Compositing Semantic Bubble for Hybrid Processing...")
        # Masks shape is (num_boxes, 3, H, W). Take highest quality (index 0).
        best_masks = masks[:, 0, :, :]
        
        # Combine all masks via logical OR
        combined_mask = torch.any(best_masks, dim=0).float().unsqueeze(0).unsqueeze(0)
        
        # THE HYBRID TRICK: SAM 2 makes jagged edges that cut off soft hair/glows.
        # We dilate (expand) the mask outwards by ~40 pixels. This creates a safe "bubble"
        # that catches all the soft, fading pixels SAM 2 missed.
        kernel_size = 81 # A large kernel to ensure we capture all glowing pixels
        dilated_mask_tensor = F.max_pool2d(combined_mask, kernel_size=kernel_size, stride=1, padding=kernel_size//2)
        dilated_mask = dilated_mask_tensor.squeeze().numpy() > 0.5
        
        # Create output image: Keep original pixels inside the bubble, turn everything else Pure White.
        # This gives RMBG-2.0 an incredibly easy job in the next step.
        img_array = np.array(image)
        white_bg = np.ones_like(img_array) * 255
        
        hybrid_input_array = np.where(dilated_mask[..., None], img_array, white_bg)
        final_pil = Image.fromarray(hybrid_input_array, mode="RGB")
        
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        out_path = os.path.join(self.output_dir, f"{base_name}_sam2_isolated.png")
        final_pil.save(out_path)
        
        print(f"[OK] Semantic Isolation complete: {out_path}")
        return out_path
