import time
import json
import os
import subprocess

try:
    import pyautogui
    import pytesseract
    from PIL import ImageGrab
except ImportError:
    pass

def gui_click_text(target_text: str) -> str:
    """
    Takes a screenshot, uses local OCR to find the target_text, and clicks it.
    """
    try:
        screenshot_path = "/tmp/jarvis_screen.png"
        
        # Use macOS screencapture for reliability
        subprocess.run(["screencapture", "-x", screenshot_path], check=True)
        
        # Use pytesseract to find text
        from PIL import Image
        img = Image.open(screenshot_path)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        # Build a clean list of valid words with their bounding boxes
        valid_words = []
        for i, word in enumerate(data['text']):
            if word and word.strip():
                valid_words.append({
                    'text': word.strip().lower(),
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'w': data['width'][i],
                    'h': data['height'][i]
                })
        
        target_words = [w.lower() for w in target_text.split()]
        found = False
        
        for i in range(len(valid_words)):
            # Check if the sequence of target words matches here
            match = True
            for j in range(len(target_words)):
                if i + j >= len(valid_words):
                    match = False
                    break
                # Allow partial matches (e.g. 'Log' inside 'Login')
                if target_words[j] not in valid_words[i+j]['text'] and valid_words[i+j]['text'] not in target_words[j]:
                    match = False
                    break
                    
            if match:
                # Calculate center of the entire matched phrase
                first_word = valid_words[i]
                last_word = valid_words[i + len(target_words) - 1]
                
                x1 = first_word['x']
                y1 = first_word['y']
                x2 = last_word['x'] + last_word['w']
                y2 = max(first_word['y'] + first_word['h'], last_word['y'] + last_word['h'])
                
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                # Mac Retina screens often have 2x scaling. Divide by 2 for pyautogui coordinates.
                logical_x = center_x / 2
                logical_y = center_y / 2
                
                pyautogui.moveTo(logical_x, logical_y, duration=0.5, tween=pyautogui.easeInOutQuad)
                pyautogui.click()
                found = True
                break
                
        # Clean up
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
            
        if found:
            return json.dumps({"status": "success", "message": f"Clicked on '{target_text}'"})
        else:
            return json.dumps({"status": "error", "message": f"Could not find text '{target_text}' on screen. Ensure it is visible."})
            
    except Exception as e:
        return json.dumps({"status": "error", "message": f"GUI Automation error: {str(e)}"})

def gui_type_text(text: str) -> str:
    try:
        pyautogui.write(text, interval=0.03)
        return json.dumps({"status": "success", "message": f"Typed text successfully"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def gui_press_shortcut(keys: str) -> str:
    """
    Keys can be 'command+c', 'enter', etc.
    """
    try:
        key_list = [k.strip() for k in keys.split('+')]
        pyautogui.hotkey(*key_list)
        return json.dumps({"status": "success", "message": f"Pressed shortcut '{keys}'"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})
