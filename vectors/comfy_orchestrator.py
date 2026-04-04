import os
import json
import uuid
import random
import urllib.request
import urllib.parse
import websocket # pip install websocket-client
import argparse

class ComfyUIOrchestrator:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.output_dir = os.path.join(os.getcwd(), "outputs")
        os.makedirs(self.output_dir, exist_ok=True)

    def queue_prompt(self, prompt_workflow):
        p = {"prompt": prompt_workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        try:
            req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
            response = urllib.request.urlopen(req)
            return json.loads(response.read())
        except urllib.error.URLError:
            print("[X] ERROR: Could not connect to ComfyUI.")
            print("[!] Is ComfyUI running? Make sure to start it using:")
            print("    conda run -n comfy_vectors python main.py --lowvram --cpu-text-encoder")
            exit(1)

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        req = urllib.request.Request(f"http://{self.server_address}/view?{url_values}")
        return urllib.request.urlopen(req).read()

    def get_history(self, prompt_id):
        req = urllib.request.Request(f"http://{self.server_address}/history/{prompt_id}")
        response = urllib.request.urlopen(req)
        return json.loads(response.read())

    def generate_image(self, prompt_workflow):
        print(f"[*] Submitting workflow to ComfyUI ({self.server_address})...")
        
        try:
            ws = websocket.WebSocket()
            ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
        except ConnectionRefusedError:
            print("[X] ERROR: WebSocket connection refused. ComfyUI is not running.")
            exit(1)
            
        queue_response = self.queue_prompt(prompt_workflow)
        prompt_id = queue_response['prompt_id']
        print(f"[*] Job successfully queued. Prompt ID: {prompt_id}")

        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        print("[OK] ComfyUI execution complete.")
                        break # Execution is done
            else:
                continue

        ws.close()

        # Retrieve the generated image
        print("[*] Downloading resulting image from server...")
        history = self.get_history(prompt_id)[prompt_id]
        
        saved_paths = []
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                for image in node_output['images']:
                    image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                    
                    save_path = os.path.join(self.output_dir, image['filename'])
                    with open(save_path, "wb") as f:
                        f.write(image_data)
                    print(f"[OK] Saved artwork to: {save_path}")
                    saved_paths.append(save_path)
                    
        if not saved_paths:
            print("[X] No image found in ComfyUI output history.")
            return None
            
        return saved_paths[0]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ComfyUI Flux GGUF Orchestrator")
    parser.add_argument("--prompt", type=str, required=True, help="The artistic description to generate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for deterministic generation")
    args = parser.parse_args()

    workflow_path = "flux_schnell_api.json"
    
    if not os.path.exists(workflow_path):
        print(f"[X] ERROR: Missing API workflow file: {workflow_path}")
        exit(1)
        
    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow = json.load(f)
        
    # --- DYNAMIC INJECTION ---
    # Node "6" is the Positive Prompt
    # Node "3" is the KSampler (holds the seed)
    
    workflow["6"]["inputs"]["text"] = args.prompt
    
    seed = args.seed if args.seed is not None else random.randint(1, 999999999999999)
    workflow["3"]["inputs"]["seed"] = seed
    
    print(f"[*] Prompt: '{args.prompt}'")
    print(f"[*] Seed:   {seed}")
    
    orchestrator = ComfyUIOrchestrator()
    orchestrator.generate_image(workflow)