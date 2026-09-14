#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Scraper para Venex usando requests + BeautifulSoup
Más rápido y menos detectable que Playwright
"""

import requests
import json
import re
from typing import List, Set, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import logging
from datetime import datetime
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    logger.error("BeautifulSoup4 no instalado. Instalando...")
    import subprocess
    subprocess.run(["pip", "install", "beautifulsoup4"], check=True)
    from bs4 import BeautifulSoup


class VenexScraperRequests:
    """Scraper usando requests - más rápido y confiable"""
    
    def __init__(self):
        self.base_url = "https://www.venex.com.ar"
        self.products: List[Dict[str, Any]] = []
        self.seen_titles: Set[str] = set()
        self.visited_urls: Set[str] = set()
        
        # Session con headers realistas
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'es-AR,es;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': self.base_url
        })
    
    def fetch_page(self, url: str, retries: int = 3) -> Optional[str]:
        """Descargar página con reintentos"""
        for attempt in range(retries):
            try:
                logger.debug(f"Descargando {url} (intento {attempt + 1}/{retries})")
                
                response = self.session.get(url, timeout=15)
                response.raise_for_status()
                
                logger.info(f"✓ Página descargada: {url[:60]}...")
                return response.text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error en intento {attempt + 1}: {e}")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Esperando {wait_time}s antes de reintentar...")
                    time.sleep(wait_time)
        
        logger.error(f"✗ No se pudo descargar {url}")
        return None
    
    def extract_price(self, price_text: str) -> Optional[float]:
        """Extraer precio"""
        try:
            if not price_text:
                return None
            
            # Buscar patrón de precio
            match = re.search(r'\$?\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)', price_text)
            if not match:
                return None
            
            price_str = match.group(1)
            
            # Limpiar formato
            if price_str.count('.') > 1:
                price_str = price_str.replace('.', '').replace(',', '.')
            elif price_str.count(',') == 1 and ',' in price_str:
                price_str = price_str.replace(',', '.')
            
            price = float(price_str)
            
            # Validar rango
            if price < 100 or price > 50_000_000:
                return None
            
            return price
        except:
            return None
    
    def extract_products_from_html(self, html: str, category: str) -> List[Dict[str, Any]]:
        """Extraer productos del HTML"""
        products = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar productos - probamos múltiples selectores
            product_selectors = [
                '[class*="product"]',
                '[class*="item"]',
                '[class*="card"]',
                'article',
                '[data-product]'
            ]
            
            product_elements = []
            for selector in product_selectors:
                elements = soup.select(selector)
                if len(elements) > 2:  # Al menos 3 elementos
                    product_elements = elements
                    logger.info(f"✓ Encontrados {len(elements)} productos con selector '{selector}'")
                    break
            
            if not product_elements:
                logger.warning("⚠ No se encontraron productos")
                return products
            
            for idx, element in enumerate(product_elements):
                try:
                    # Extraer título
                    title = None
                    for tag in element.find_all(['h2', 'h3', 'h4', 'a', 'span']):
                        text = tag.get_text(strip=True)
                        if text and len(text) > 5 and len(text) < 300:
                            title = text
                            break
                    
                    if not title:
                        continue
                    
                    title = re.sub(r'\s+', ' ', title)[:250]
                    
                    # Duplicados
                    norm_title = title.lower().strip()
                    if norm_title in self.seen_titles:
                        continue
                    self.seen_titles.add(norm_title)
                    
                    # Extraer precio
                    price_text = element.get_text()
                    prices = re.findall(r'\$\s*[0-9.,]+', price_text)
                    
                    if not prices:
                        continue
                    
                    cost = self.extract_price(prices[0])
                    if not cost:
                        continue
                    
                    # Precio de venta
                    selling_price = round(cost * 1.15, 2)
                    
                    # Extraer imagen
                    image_url = ""
                    img_tag = element.find('img')
                    if img_tag:
                        src = img_tag.get('src') or img_tag.get('data-src')
                        if src and 'placeholder' not in src.lower():
                            image_url = urljoin(self.base_url, src)
                    
                    product = {
                        "titulo": title,
                        "categoria": category,
                        "precio_costo": cost,
                        "precio_venta": selling_price,
                        "imagen": image_url,
                        "stock": True
                    }
                    
                    products.append(product)
                    logger.info(f"✓ [{len(products)}] {title[:35]}... | ${cost} → ${selling_price}")
                    
                except Exception as e:
                    logger.debug(f"Error extrayendo producto {idx}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"✗ Error parseando HTML: {e}")
        
        return products
    
    def discover_categories(self) -> List[tuple]:
        """Descubrir categorías desde página principal"""
        categories = []
        try:
            logger.info("🔍 Descubriendo categorías...")
            
            html = self.fetch_page(self.base_url)
            if not html:
                return categories
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar links en navegación
            nav = soup.find(['nav', 'header']) or soup
            links = nav.find_all('a', href=True)
            
            for link in links:
                href = link.get('href')
                text = link.get_text(strip=True)
                
                if not href or not text or len(text) < 2 or len(text) > 100:
                    continue
                
                if href.startswith('#') or 'javascript:' in href:
                    continue
                
                full_url = urljoin(self.base_url, href)
                
                if 'venex.com.ar' in full_url and full_url not in self.visited_urls:
                    categories.append((text, full_url))
                    logger.debug(f"  - {text}: {full_url}")
            
            # Remover duplicados
            categories = list(set(categories))
            logger.info(f"✓ Descubiertas {len(categories)} categorías")
            
            return categories
            
        except Exception as e:
            logger.error(f"✗ Error descubriendo categorías: {e}")
            return categories
    
    def scrape_with_pagination(self, url: str, category: str) -> List[Dict[str, Any]]:
        """Scrapear categoría con paginación"""
        all_products = []
        page_num = 1
        max_pages = 100
        
        try:
            while page_num <= max_pages:
                logger.info(f"📄 Página {page_num}")
                
                # Intentar URL con parámetro de página
                page_url = f"{url}?page={page_num}" if '?' not in url else f"{url}&page={page_num}"
                
                html = self.fetch_page(page_url)
                if not html:
                    break
                
                products = self.extract_products_from_html(html, category)
                
                if not products:
                    logger.info("ℹ Página sin productos, finalizando")
                    break
                
                all_products.extend(products)
                page_num += 1
                
                time.sleep(1)  # Respetar servidor
                
        except Exception as e:
            logger.error(f"✗ Error en paginación: {e}")
        
        return all_products
    
    def scrape_category(self, category_name: str, category_url: str) -> List[Dict[str, Any]]:
        """Scrapear una categoría"""
        try:
            if category_url in self.visited_urls:
                return []
            
            self.visited_urls.add(category_url)
            
            logger.info(f"\n{'='*70}")
            logger.info(f"🔗 {category_name}")
            logger.info(f"   {category_url}")
            logger.info(f"{'='*70}")
            
            products = self.scrape_with_pagination(category_url, category_name)
            logger.info(f"✓ {len(products)} productos extraídos")
            
            return products
            
        except Exception as e:
            logger.error(f"✗ Error scrapeando {category_name}: {e}")
            return []
    
    def save_products(self, filename: str = "productos.json"):
        """Guardar productos"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=4)
            logger.info(f"✓ {len(self.products)} productos guardados en {filename}")
            return True
        except Exception as e:
            logger.error(f"✗ Error guardando: {e}")
            return False
    
    def run(self):
        """Ejecutar scraper"""
        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"🚀 VENEX SCRAPER (Requests + BeautifulSoup)")
            logger.info(f"   Inicio: {datetime.now().isoformat()}")
            logger.info(f"{'='*70}\n")
            
            # Descubrir categorías
            categories = self.discover_categories()
            
            if not categories:
                logger.error("✗ No se pudieron descubrir categorías")
                return 1
            
            # Scrapear cada categoría
            for idx, (cat_name, cat_url) in enumerate(categories, 1):
                try:
                    logger.info(f"\n[{idx}/{len(categories)}] Procesando {cat_name}...")
                    products = self.scrape_category(cat_name, cat_url)
                    self.products.extend(products)
                    
                except Exception as e:
                    logger.error(f"✗ Error en categoría {cat_name}: {e}")
                    continue
            
            # Resumen
            logger.info(f"\n{'='*70}")
            logger.info(f"📊 RESUMEN")
            logger.info(f"{'='*70}")
            logger.info(f"Total productos: {len(self.products)}")
            logger.info(f"Categorías únicas: {len(set(p['categoria'] for p in self.products))}")
            
            if self.save_products():
                logger.info(f"✅ COMPLETADO")
                return 0
            else:
                return 1
            
        except Exception as e:
            logger.error(f"❌ ERROR FATAL: {e}", exc_info=True)
            return 1


def main():
    """Punto de entrada"""
    scraper = VenexScraperRequests()
    return scraper.run()


if __name__ == "__main__":
    exit(main())
