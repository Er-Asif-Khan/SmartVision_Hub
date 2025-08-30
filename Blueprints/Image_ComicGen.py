from flask import render_template, Blueprint, request, jsonify, url_for
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
import os
import cv2
import mediapipe as mp

imgComicGen_bp = Blueprint('imgComicGen_bp', __name__)

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

load_dotenv()

GITHUB_PAT = os.getenv('GITHUB_PAT')

def generate_text(genre, count):
    token = GITHUB_PAT
    endpoint = "https://models.github.ai/inference"
    model_name = "openai/gpt-4o"

    client = OpenAI(
        base_url=endpoint,
        api_key=token,
    )
    
    prompt = f"Write {count} short comic-style dialogue lines in the {genre} genre.Each line must be **no more than 5 words**, witty, casual, and suitable for speech bubbles in a comic with human characters.Avoid numbering or labels.Keep the tone humorous or expressive depending on the genre. and remove '*' from all sentences and don't start sentence with '-' and don't enclose the sentence in "" (quotes), make the comic in easy humor and meaningful even in 2 peoples and make sure you generate unique and best dialogues every time."

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant.",
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=1.0,
        top_p=1.0,
        max_tokens=20 * count,
        model=model_name
    )

    raw_output = response.choices[0].message.content.strip()
    lines = [line.strip() for line in raw_output.split("\n") if line.strip()]
    return lines

def assign_bubbles(image_np, heads, texts):
    h, w = image_np.shape[:2]
    heads_sorted = sorted(heads, key=lambda x: x['x'])  # sort left to right
    num_heads = len(heads_sorted)
    out = []

    def space_left(head):
        return head['top_l'][0]

    def space_right(head):
        return w - head['bottom_r'][0]

    def space_between(h1, h2):
        return h2['top_l'][0] - h1['bottom_r'][0]

    def calc_font_size(bubble_w):
        return max(12, min(28, int(bubble_w / (5 * 6))))

    if num_heads == 2:
        left_space = space_left(heads_sorted[0])
        right_space = space_right(heads_sorted[1])
        between_space = space_between(heads_sorted[0], heads_sorted[1])

        spaces = [
            ("left", left_space),
            ("between", between_space),
            ("right", right_space)
        ]
        best_two = sorted(spaces, key=lambda x: x[1], reverse=True)[:2]

        if all(space[0] != "left" for space in best_two):
            bx_left = heads_sorted[0]['bottom_r'][0] + between_space // 2 - int(heads_sorted[0]['radius'] * 0.8)
            by_left = heads_sorted[0]['y'] - heads_sorted[0]['radius'] - int(heads_sorted[0]['radius'] * 0.8)
            bw_left = int(heads_sorted[0]['radius'] * 2)
            out.append({**heads_sorted[0], "text": texts[0], "font_size": calc_font_size(bw_left), "head": 0, "pos": (bx_left, by_left), "bubble_width": bw_left})

            bx_right = heads_sorted[1]['bottom_r'][0] + int(heads_sorted[1]['radius'] * 0.5)
            by_right = heads_sorted[1]['y'] - heads_sorted[1]['radius'] - int(heads_sorted[1]['radius'] * 0.8)
            bw_right = int(heads_sorted[1]['radius'] * 2)
            out.append({**heads_sorted[1], "text": texts[1], "font_size": calc_font_size(bw_right), "head": 1, "pos": (bx_right, by_right), "bubble_width": bw_right})

        elif all(space[0] != "between" for space in best_two):
            bx_left = heads_sorted[0]['top_l'][0] - int(heads_sorted[0]['radius'] * 1.2)
            by_left = heads_sorted[0]['y'] - heads_sorted[0]['radius'] - int(heads_sorted[0]['radius'] * 0.8)
            bw_left = int(heads_sorted[0]['radius'] * 2)
            out.append({**heads_sorted[0], "text": texts[0], "font_size": calc_font_size(bw_left), "head": 0, "pos": (bx_left, by_left), "bubble_width": bw_left})

            bx_right = heads_sorted[1]['bottom_r'][0] + int(heads_sorted[1]['radius'] * 0.5)
            by_right = heads_sorted[1]['y'] - heads_sorted[1]['radius'] - int(heads_sorted[1]['radius'] * 0.8)
            bw_right = int(heads_sorted[1]['radius'] * 2)
            out.append({**heads_sorted[1], "text": texts[1], "font_size": calc_font_size(bw_right), "head": 1, "pos": (bx_right, by_right), "bubble_width": bw_right})

        elif all(space[0] != "right" for space in best_two):
            bx_left = heads_sorted[0]['top_l'][0] - int(heads_sorted[0]['radius'] * 1.2)
            by_left = heads_sorted[0]['y'] - heads_sorted[0]['radius'] - int(heads_sorted[0]['radius'] * 0.8)
            bw_left = int(heads_sorted[0]['radius'] * 2)
            out.append({**heads_sorted[0], "text": texts[0], "font_size": calc_font_size(bw_left), "head": 0, "pos": (bx_left, by_left), "bubble_width": bw_left})

            bx_right = heads_sorted[1]['top_l'][0] - between_space // 2
            by_right = heads_sorted[1]['y'] - heads_sorted[1]['radius'] - int(heads_sorted[1]['radius'] * 0.8)
            bw_right = int(heads_sorted[1]['radius'] * 2)
            out.append({**heads_sorted[1], "text": texts[1], "font_size": calc_font_size(bw_right), "head": 1, "pos": (bx_right, by_right), "bubble_width": bw_right})



    # elif num_heads == 3:

        # def no_overlap(pos1, w1, pos2, w2):
        # """Shift pos2 right if overlapping pos1."""
        # x1, _ = pos1
        # x2, _ = pos2
        # if abs(x2 - x1) < (w1 // 2 + w2 // 2):
        #     return (x2 + (w1 // 2 + w2 // 2) + 5, pos2[1])  # small gap
        # return pos2

        # Will Code further

        # left_space = space_left(heads_sorted[0])
        # right_space = space_right(heads_sorted[2])

    #     if left_space < heads_sorted[0]['radius']:
    #     # Left bubble (top middle)
    #     bw_left = int(heads_sorted[0]['radius'] * 2)
    #     pos_left = (heads_sorted[0]['x'] - bw_left // 2,
    #                 heads_sorted[0]['y'] - int(heads_sorted[0]['radius'] * 1.5))
    #     bubbles.append({"head": 0, "pos": pos_left, "font_size": calc_font_size(bw_left), "text": texts[0], "bubble_width": bw_left})

    #     # Middle bubble (between left top middle & middle top right)
    #     gap = heads_sorted[1]['top_l'][0] - heads_sorted[0]['x']
    #     bw_mid = int(heads_sorted[1]['radius'] * 2)
    #     pos_mid = (heads_sorted[0]['x'] + gap // 2 - bw_mid // 2,
    #                heads_sorted[1]['y'] - int(heads_sorted[1]['radius'] * 1.5))
    #     pos_mid = no_overlap(pos_left, bw_left, pos_mid, bw_mid)
    #     bubbles.append({"head": 1, "pos": pos_mid, "font_size": calc_font_size(bw_mid), "text": texts[1], "bubble_width": bw_mid})

    #     # Right bubble (top right)
    #     bw_right = int(heads_sorted[2]['radius'] * 2)
    #     pos_right = (heads_sorted[2]['bottom_r'][0],
    #                  heads_sorted[2]['y'] - int(heads_sorted[2]['radius'] * 1.5))
    #     pos_right = no_overlap(pos_mid, bw_mid, pos_right, bw_right)
    #     bubbles.append({"head": 2, "pos": pos_right, "font_size": calc_font_size(bw_right), "text": texts[2], "bubble_width": bw_right})

    # # Scenario 2: No right space
    # elif right_space < heads_sorted[2]['radius']:
    #     # Left bubble (top left)
    #     bw_left = int(heads_sorted[0]['radius'] * 2)
    #     pos_left = (heads_sorted[0]['top_l'][0] - bw_left,
    #                 heads_sorted[0]['y'] - int(heads_sorted[0]['radius'] * 1.5))
    #     bubbles.append({"head": 0, "pos": pos_left, "font_size": calc_font_size(bw_left), "text": texts[0], "bubble_width": bw_left})

    #     # Middle bubble (between left top left & middle top middle)
    #     gap = heads_sorted[1]['x'] - heads_sorted[0]['top_l'][0]
    #     bw_mid = int(heads_sorted[1]['radius'] * 2)
    #     pos_mid = (heads_sorted[0]['top_l'][0] + gap // 2 - bw_mid // 2,
    #                heads_sorted[1]['y'] - int(heads_sorted[1]['radius'] * 1.5))
    #     pos_mid = no_overlap(pos_left, bw_left, pos_mid, bw_mid)
    #     bubbles.append({"head": 1, "pos": pos_mid, "font_size": calc_font_size(bw_mid), "text": texts[1], "bubble_width": bw_mid})

    #     # Right bubble (top left)
    #     bw_right = int(heads_sorted[2]['radius'] * 2)
    #     pos_right = (heads_sorted[2]['top_l'][0] - bw_right,
    #                  heads_sorted[2]['y'] - int(heads_sorted[2]['radius'] * 1.5))
    #     pos_right = no_overlap(pos_mid, bw_mid, pos_right, bw_right)
    #     bubbles.append({"head": 2, "pos": pos_right, "font_size": calc_font_size(bw_right), "text": texts[2], "bubble_width": bw_right})


    return out


def detect_heads(image_np):
    mp_face = mp.solutions.face_detection
    with mp_face.FaceDetection(model_selection = 1, min_detection_confidence = 0.6) as fd:

        rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)  
        results = fd.process(rgb)
        heads = []

        if results.detections:
            img_h, img_w, _ = image_np.shape

            for det in results.detections:
    
                if det.score[0] > 0.4:
                    bbox = det.location_data.relative_bounding_box

                    x_center = int((bbox.xmin + bbox.width / 2) * img_w)
                    y_center = int((bbox.ymin + bbox.height / 2) * img_h)
                    radius = int(max(bbox.width * img_w, bbox.height * img_h) / 2) 

                    # if radius > 30:
                    #     radius = int(radius + ((4 / radius) * 100))
                    #     y_center = int(y_center - ((10/radius) * 100))
                    # elif radius < 30 and radius > 20:
                    #     radius = int(radius + ((2 / radius) * 100))
                    #     y_center = int(y_center - ((5/radius) * 100))
                    # elif radius < 20 and radius > 15:
                    #     radius = int(radius + ((2 / radius) * 100))
                    #     y_center = int(y_center - ((2/radius) * 100))
                        

                    top_left = (x_center - radius, y_center - radius)
                    bottom_right = (x_center + radius, y_center + radius)

                    heads.append({'x': x_center, 'y': y_center, 'radius': radius, 'top_l': top_left, 'bottom_r': bottom_right})
        return heads
    
@imgComicGen_bp.route('/')
def index():
    return render_template('index_comic.html', show_image = False)

@imgComicGen_bp.route('/comicgen', methods = ['POST', 'GET'])
def comicgen():
    if request.method == 'POST':
        image_file = request.files['image']
        genre = request.form.get('genre')
        image = Image.open(image_file.stream).convert('RGB')
        image_np = np.array(image)
        heads = detect_heads(image_np)

        if not heads:
            return jsonify({'error': 'No Heads Found'})
        
        texts = generate_text(genre, len(heads))

        bubbles = assign_bubbles(image_np, heads, texts)

        height, width = image_np.shape[:2]

        return jsonify({
            "heads": bubbles,
            "original_width": width, 
            "original_height": height
        })
    return render_template('index_comic.html', show_image = True)
