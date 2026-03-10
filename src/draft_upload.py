# -*- coding: utf-8 -*-
import requests
import yaml
import json
import io
import re
import os
import numpy as np
import base64
import cv2
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from PIL import Image
from playwright.sync_api import sync_playwright

def load_config():
    with open('wechat.yml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_access_token(appid, secret):
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(appid, secret)
    resp = requests.get(url)
    data = resp.json()
    if 'access_token' in data:
        return data['access_token']
    else:
        raise Exception('获取access_token失败: {}'.format(data))

def load_image_array(image_data):
    img = Image.open(io.BytesIO(image_data))
    rgb = np.array(img.convert('RGB'))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def encode_image_array(image_bgr, quality=95):
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    output = io.BytesIO()
    Image.fromarray(rgb).save(output, format='JPEG', quality=quality)
    return output.getvalue()


def write_debug_artifacts(original_bgr, mask, cleaned_bgr):
    if os.getenv('WATERMARK_DEBUG') != '1':
        return

    debug_dir = os.getenv('WATERMARK_DEBUG_DIR', '.')
    os.makedirs(debug_dir, exist_ok=True)

    Image.fromarray(cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB)).save(
        os.path.join(debug_dir, 'debug_original.jpg'),
        format='JPEG',
        quality=95,
    )
    Image.fromarray(mask).save(os.path.join(debug_dir, 'debug_mask.png'), format='PNG')
    Image.fromarray(cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2RGB)).save(
        os.path.join(debug_dir, 'debug_clean.jpg'),
        format='JPEG',
        quality=95,
    )


def score_watermark_candidate(component_mask):
    ys, xs = np.where(component_mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        return 0.0

    roi_h, roi_w = component_mask.shape
    area = float(len(xs))
    area_ratio = area / float(roi_h * roi_w)
    x_min, x_max = xs.min(), xs.max()
    y_min, y_max = ys.min(), ys.max()
    bbox_w = x_max - x_min + 1
    bbox_h = y_max - y_min + 1
    bbox_area = float((x_max - x_min + 1) * (y_max - y_min + 1))
    bbox_area_ratio = bbox_area / float(roi_h * roi_w)
    bbox_width_ratio = bbox_w / float(roi_w)
    bbox_height_ratio = bbox_h / float(roi_h)
    fill_ratio = area / max(bbox_area, 1.0)
    right_bias = max(0.0, ((x_max + 1) / float(roi_w) - 0.65) / 0.35)
    bottom_bias = max(0.0, ((y_max + 1) / float(roi_h) - 0.60) / 0.40)

    if bbox_area_ratio > 0.60 or (bbox_width_ratio > 0.85 and bbox_height_ratio > 0.55):
        return 0.0

    score = min(area_ratio / 0.08, 0.20)
    score += min(bbox_area_ratio / 0.20, 0.25)
    score += min(right_bias, 1.0) * 0.20
    score += min(bottom_bias, 1.0) * 0.20
    if fill_ratio >= 0.18:
        score += 0.15
    elif bbox_area_ratio >= 0.08:
        score += 0.12

    return score


def detect_watermark_mask(image_bgr):
    height, width = image_bgr.shape[:2]
    roi_w = max(1, int(width * 0.30))
    roi_h = max(1, int(height * 0.22))
    x0 = width - roi_w
    y0 = height - roi_h
    roi = image_bgr[y0:height, x0:width]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    value = hsv[:, :, 2]
    saturation = hsv[:, :, 1]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    value_threshold = min(255, max(185, int(np.mean(value) + 18)))
    bright_mask = np.where((value >= value_threshold) & (saturation <= 115), 255, 0).astype(np.uint8)
    bright_mask = cv2.morphologyEx(
        bright_mask,
        cv2.MORPH_CLOSE,
        np.ones((5, 5), dtype=np.uint8),
    )
    bright_mask = cv2.morphologyEx(
        bright_mask,
        cv2.MORPH_OPEN,
        np.ones((3, 3), dtype=np.uint8),
    )

    edge_map = cv2.Canny(gray, 80, 180)
    edge_density = cv2.blur((edge_map > 0).astype(np.float32), (11, 11))
    edge_mask = np.where(edge_density >= 0.10, 255, 0).astype(np.uint8)
    edge_mask = cv2.dilate(edge_mask, np.ones((9, 9), dtype=np.uint8), iterations=1)
    edge_mask = cv2.morphologyEx(
        edge_mask,
        cv2.MORPH_CLOSE,
        np.ones((11, 11), dtype=np.uint8),
    )

    candidate_mask = cv2.bitwise_or(bright_mask, edge_mask)

    label_count, labels, stats, _ = cv2.connectedComponentsWithStats(candidate_mask, 8)
    best_mask = None
    best_score = 0.0
    min_area = max(120, int(roi_w * roi_h * 0.005))

    for label in range(1, label_count):
        area = stats[label, cv2.CC_STAT_AREA]
        if area < min_area:
            continue

        component_mask = np.where(labels == label, 255, 0).astype(np.uint8)
        score = score_watermark_candidate(component_mask)
        if score > best_score:
            best_score = score
            best_mask = component_mask

    full_mask = np.zeros((height, width), dtype=np.uint8)
    roi_bounds = (x0, y0, roi_w, roi_h)

    if best_mask is None:
        return full_mask, roi_bounds, 0.0

    best_mask = cv2.dilate(best_mask, np.ones((5, 5), dtype=np.uint8), iterations=1)
    full_mask[y0:height, x0:width] = best_mask
    return full_mask, roi_bounds, best_score


def inpaint_watermark(image_bgr, mask, roi_bounds):
    x0, y0, roi_w, roi_h = roi_bounds
    cleaned = image_bgr.copy()
    roi_image = cleaned[y0:y0 + roi_h, x0:x0 + roi_w]
    roi_mask = mask[y0:y0 + roi_h, x0:x0 + roi_w]
    cleaned[y0:y0 + roi_h, x0:x0 + roi_w] = cv2.inpaint(roi_image, roi_mask, 3, cv2.INPAINT_TELEA)
    return cleaned

def remove_watermark(image_data):
    try:
        image_bgr = load_image_array(image_data)
        mask, roi_bounds, score = detect_watermark_mask(image_bgr)

        if score < 0.6 or np.count_nonzero(mask) == 0:
            print("    未检测到高置信度水印，保留原图")
            return image_data

        print("    检测到水印，置信度: {:.2f}".format(score))
        cleaned = inpaint_watermark(image_bgr, mask, roi_bounds)
        write_debug_artifacts(image_bgr, mask, cleaned)
        return encode_image_array(cleaned, quality=95)
    except Exception as e:
        print("    图像处理失败: {}，保留原图".format(e))
        return image_data

def modify_image_md5(image_data):
    return image_data + b'\x00'

def upload_permanent_image(access_token, image_data):
    url = 'https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={}&type=image'.format(access_token)
    files = {'media': ('image.jpg', io.BytesIO(image_data), 'image/jpeg')}
    result = requests.post(url, files=files)
    return result.json()

def upload_draft(access_token, articles):
    url = 'https://api.weixin.qq.com/cgi-bin/draft/add?access_token={}'.format(access_token)
    data = {"articles": articles}
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    resp = requests.post(url, data=json.dumps(data, ensure_ascii=False).encode('utf-8'), headers=headers)
    return resp.json()

def fetch_article_images(article_url):
    images = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(article_url, wait_until='networkidle')
        page.wait_for_timeout(5000)
        
        js_content = page.query_selector('#js_content')
        if js_content:
            print('  文章内容长度: {} 字符'.format(len(js_content.inner_text())))
        
        img_elements = page.query_selector_all('img[data-src]')
        print('  找到 {} 个图片元素'.format(len(img_elements)))
        
        for img in img_elements:
            data_src = img.get_attribute('data-src')
            if data_src and 'mmbiz' in data_src:
                images.append(data_src)
        
        browser.close()
    
    seen = set()
    return [x for x in images if not (x in seen or seen.add(x))]

def main():
    config = load_config()
    appid = config['wechat']['appid']
    secret = config['wechat']['secret']
    author = config['wechat']['author']
    
    article_url = "https://mp.weixin.qq.com/s/yq_btzDPwT8yvRMv5aetog"
    
    print("正在获取 access_token...")
    access_token = get_access_token(appid, secret)
    print("access_token 获取成功")
    
    print("\n正在抓取原文图片...")
    image_urls = fetch_article_images(article_url)
    print("发现 {} 张图片".format(len(image_urls)))
    
    print("\n正在处理图片...")
    uploaded_images = []
    cover_image_data = None
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://mp.weixin.qq.com/'
    }
    for i, img_url in enumerate(image_urls[:5]):
        print("  处理图片 {}/5...".format(i+1))
        try:
            resp = requests.get(img_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                clean_image = remove_watermark(resp.content)
                if i == 0:
                    cover_image_data = modify_image_md5(clean_image)
                modified_data = modify_image_md5(clean_image)
                result = upload_permanent_image(access_token, modified_data)
                if 'url' in result:
                    uploaded_images.append(result['url'])
                    print("    上传成功")
            else:
                print("    下载失败: HTTP {}".format(resp.status_code))
        except Exception as e:
            print("    处理失败: {}".format(e))
    
    print("\n正在上传封面图片（使用原文第一张图）...")
    if cover_image_data:
        img_result = upload_permanent_image(access_token, cover_image_data)
    else:
        cover_resp = requests.get("https://picsum.photos/900/383")
        img_result = upload_permanent_image(access_token, cover_resp.content)
    
    if 'media_id' not in img_result:
        print("封面上传失败: {}".format(img_result))
        return
    
    thumb_media_id = img_result['media_id']
    print("封面上传成功")
    
    title = "OpenClaw新版本：上下文管理终于自由了"
    
    para1 = '<section style="padding:20px;font-family:-apple-system,sans-serif;"><p style="font-size:16px;line-height:1.8;color:#333;">说实话，最近龙虾（Claude）不稳定搞得我头太大了。<br/><br/>就在我快被折腾疯的时候，OpenClaw发布了v2026.3.7-beta.1版本——89项提交、200+Bug修复。最让我心动的，是全新的ContextEngine插件接口。<br/><br/>上下文管理，终于可以「自由插拔」了。</p></section>'
    
    para2 = '<section style="padding:20px;background:#f8f9fa;border-radius:8px;margin:20px0;"><h2 style="color:#2c3e50;border-left:4px solid #3498db;padding-left:12px;">这次更新有多猛？</h2><p style="font-size:15px;line-height:1.8;">OpenClaw创始人Peter Steinberger亲自官宣，这个版本的提交密度是史上最高的。<br/><br/>我看了下更新日志，几个核心看点：<br/>* GPT-5.4 + Gemini 3.1 Flash 双引擎首发适配<br/>* ContextEngine插件接口——开发者等了半年的功能<br/>* 200+ Bug修复，几乎翻修了一遍<br/>* Discord + Telegram深度整合</p></section>'
    
    para3 = '<section style="padding:20px;"><h2 style="color:#2c3e50;border-left:4px solid #e74c3c;padding-left:12px;">ContextEngine：最硬核的更新</h2><p style="font-size:15px;line-height:1.8;">做过AI应用的朋友都知道，上下文管理是最让人头疼的问题之一。<br/><br/>对话轮次一多，token就炸；信息一压缩，关键细节就丢。<br/><br/>这次OpenClaw开放了一组完整的生命周期钩子：<br/>* bootstrap（初始化）<br/>* ingest（注入）<br/>* assemble（组装）<br/>* compact（压缩）<br/>* afterTurn（回合后处理）<br/>* prepareSubagentSpawn（子智能体生成前）<br/>* onSubagentEnded（子智能体结束后）<br/><br/>翻译成人话：开发者现在可以在不修改核心代码的情况下，完全自定义上下文处理逻辑。想用RAG？可以。想做激进压缩？随意。</p></section>'
    
    para4 = '<section style="padding:20px;background:#e8f5e9;border-radius:8px;margin:20px0;"><h2 style="color:#2c3e50;border-left:4px solid #27ae60;padding-left:12px;">模型路由器：这个功能我等太久了</h2><p style="font-size:15px;line-height:1.8;">新版优化了模型降级与重试机制——当某个模型限流或过载时，系统会自动切换到备选模型，而不是直接报错。<br/><br/>你可以把OpenClaw想象成一个「模型路由器」。前端对接聊天工具，后端灵活挂载Claude、GPT、Gemini、DeepSeek等任意大模型。<br/><br/><strong>哪个好用用哪个，哪个便宜切哪个。</strong><br/><br/>对于被龙虾稳定性折磨的我来说，这简直是刚需——当Claude抽风的时候能自动切到GPT或Gemini，不用干等。</p></section>'
    
    para5 = '<section style="padding:20px;"><h2 style="color:#2c3e50;border-left:4px solid #9b59b6;padding-left:12px;">老张的看法</h2><p style="font-size:15px;line-height:1.8;">说实话，这个版本我绝对要试试。模型路由功能对我来说是刚需。<br/><br/>不过提醒一句：这个是beta1版本，生产环境还是谨慎使用为好。<br/><br/>我的建议是：先在测试环境跑起来，稳定了再上生产。<br/><br/>以终为始，稳扎稳打。</p></section>'
    
    para6 = '<section style="padding:20px;background:#f5f5f5;border-radius:8px;margin:20px0;"><h2 style="color:#2c3e50;border-left:4px solid #607d8b;padding-left:12px;">200+ Bug修复清单</h2><p style="font-size:15px;line-height:1.8;">这次的修复覆盖了几乎所有核心模块：<br/><br/>* 渠道层：Telegram草稿流重复、Discord断连死机、Slack消息路由、飞书Webhook兼容性<br/>* 核心智能体：工具调用参数解析、上下文压缩截断提示丢失、OpenAI流式输出兼容<br/>* 网关与内存：Token防连环掉线、QMD内存检索去重、SQLite锁冲突<br/>* 安全：依赖库升级、沙盒逃逸防范、系统命令执行白名单鉴权</p></section>'
    
    para7 = '<section style="padding:20px;"><h2 style="color:#2c3e50;border-left:4px solid #ff9800;padding-left:12px;">写在最后</h2><p style="font-size:15px;line-height:1.8;">OpenClaw这次更新，把上下文管理从「黑盒」变成了「插件」，开发者终于可以自己掌控了。<br/><br/>对于被大模型稳定性折磨的团队来说，模型路由功能是救命稻草。<br/><br/>开源的魅力就在这里：你不需要向任何厂商交租子，数据在自己手里，连接哪个模型你说了算。<br/><br/>迷雾中总有微光，探索者终会找到方向。<br/><br/><span style="font-size:14px;color:#666;">参考资料：https://github.com/openclaw/openclaw/releases/tag/v2026.3.7-beta.1</span></p></section>'
    
    paragraphs = [para1, para2, para3, para4, para5, para6, para7]
    
    print("\n正在组装文章并插入图片...")
    content_parts = []
    img_idx = 0
    for i, para in enumerate(paragraphs):
        content_parts.append(para)
        if img_idx < len(uploaded_images):
            if i in [0, 2, 3, 5]:
                img_tag = '<p style="text-align:center;margin:15px0;"><img src="{}" style="max-width:100%;border-radius:8px;"/></p>'.format(uploaded_images[img_idx])
                content_parts.append(img_tag)
                print("  图片{}插入到段落{}后".format(img_idx+1, i+1))
                img_idx += 1
    
    content = ''.join(content_parts)
    
    article = {
        "title": title,
        "author": author,
        "content": content,
        "thumb_media_id": thumb_media_id,
        "digest": "OpenClaw新版本发布，上下文管理终于自由了。模型路由功能让Claude抽风时自动切换，不用干等。",
        "content_source_url": "https://github.com/openclaw/openclaw/releases/tag/v2026.3.7-beta.1",
        "need_open_comment": 0,
        "only_fans_can_comment": 0
    }
    
    print("\n正在上传草稿...")
    result = upload_draft(access_token, [article])
    
    if 'media_id' in result:
        print("\n草稿上传成功! media_id: {}".format(result['media_id']))
    else:
        print("\n上传失败: {}".format(result))
    
    return result

if __name__ == '__main__':
    main()
