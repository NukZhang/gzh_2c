# -*- coding: utf-8 -*-
import requests
import yaml
import json
import io
import re
import numpy as np
import base64
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

def detect_watermark_by_vision(image_data):
    try:
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        
        gray = np.array(img.convert('L'))
        
        roi_w = int(width * 0.3)
        roi_h = int(height * 0.2)
        roi = gray[height - roi_h:height, width - roi_w:width]
        
        mean_val = np.mean(roi)
        std_val = np.std(roi)
        
        threshold = mean_val + std_val * 0.5
        binary = (roi > threshold).astype(np.uint8)
        
        rows = np.any(binary, axis=1)
        cols = np.any(binary, axis=0)
        
        if np.any(rows) and np.any(cols):
            row_indices = np.where(rows)[0]
            col_indices = np.where(cols)[0]
            
            min_row = np.min(row_indices)
            min_col = np.min(col_indices)
            
            watermark_y = height - roi_h + min_row
            watermark_x = width - roi_w + min_col
            
            padding = 30
            crop_x = max(0, watermark_x - padding)
            crop_y = max(0, watermark_y - padding)
            
            print("    检测到水印起点: ({}, {})".format(watermark_x, watermark_y))
            
            if watermark_x > width * 0.4 and watermark_y > height * 0.4:
                return (0, 0, crop_x, crop_y)
        
        return None
    except Exception as e:
        print("    水印检测失败: {}".format(e))
        return None

def remove_watermark(image_data):
    try:
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        
        crop_box = detect_watermark_by_vision(image_data)
        
        if crop_box:
            box = (0, 0, max(crop_box[2], int(width * 0.5)), max(crop_box[3], int(height * 0.5)))
            cropped = img.crop(box)
            print("    裁剪到: ({}, {}, {}, {})".format(*box))
        else:
            print("    未检测到水印，使用默认裁剪")
            crop_width = int(width * 0.22)
            crop_height = int(height * 0.12)
            box = (0, 0, width - crop_width, height - crop_height)
            cropped = img.crop(box)
        
        output = io.BytesIO()
        if cropped.mode in ('RGBA', 'P'):
            cropped = cropped.convert('RGB')
        cropped.save(output, format='JPEG', quality=95)
        return output.getvalue()
    except Exception as e:
        print("    图像处理失败: {}，使用默认裁剪".format(e))
        try:
            img = Image.open(io.BytesIO(image_data))
            width, height = img.size
            box = (0, 0, int(width * 0.78), int(height * 0.88))
            cropped = img.crop(box)
            output = io.BytesIO()
            if cropped.mode in ('RGBA', 'P'):
                cropped = cropped.convert('RGB')
            cropped.save(output, format='JPEG', quality=95)
            return output.getvalue()
        except:
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
