#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Scraper para Venex (https://www.venex.com.ar)
Descubre dinámicamente categorías, subcategorías y extrae catálogo completo
con margen de ganancia 15% y estructura de categorías jerárquica
"""

import asyncio
import json
import re
from typing import List, Set, Dict, Any, Optional, Tuple
from urllib.parse import urljoin
import logging

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VenexScraper:
    """Web scraper completo para Venex con categorías jerárquicas"""
    
    def __init__(self):
        self.base_url = "https://www.venex.com.ar"
        self.products: List[Dict[str, Any]] = []
        self.seen_titles: Set[str] = set()
        self.visited_urls: Set[str] = set()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.categories_tree: Dict[str, List[Tuple[str, str]]] = {}
        
    async def init_browser(self):
        """Inicializar navegador"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            logger.info("✓ Navegador inicializado")
        except Exception as e:
            logger.error(f"✗ Error inicializando navegador: {e}")
            raise
        
    async def close_browser(self):
        """Cerrar navegador"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("✓ Navegador cerrado")
        except Exception as e:
            logger.error(f"✗ Error cerrando navegador: {e}")
        
    async def goto_page(self, page: Page, url: str, wait_time: int = 3000) -> bool:
        """Navegar a URL"""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(wait_time)
            return True
        except Exception as e:
            logger.error(f"✗ Error navegando a {url}: {e}")
            return False
    
    async def discover_categories_structure(self, page: Page) -> Dict[str, List[Tuple[str, str]]]:
        """Descubrir estructura de categorías y subcategorías desde menú principal"""
        categories = {}
        try:
            await self.goto_page(page, self.base_url, wait_time=2000)
            
            logger.info("🔍 Buscando estructura de categorías...")
            
            # Buscar elementos del menú principal
            menu_items = await page.query_selector_all("nav a, .navbar a, [class*='menu'] > a, [class*='nav'] > a")
            
            for menu_item in menu_items:
                try:
                    # Obtener texto e href de categoría principal
                    text = await menu_item.text_content()
                    href = await menu_item.get_attribute("href")
                    
                    if not text or not href or text.strip() in ['', 'Home', 'Inicio']:
                        continue
                    
                    if href.startswith('#') or 'javascript:' in href:
                        continue
                    
                    cat_name = text.strip()
                    cat_url = urljoin(self.base_url, href)
                    
                    if 'venex.com.ar' not in cat_url or cat_url in self.visited_urls:
                        continue
                    
                    logger.info(f"✓ Categoría encontrada: {cat_name}")
                    categories[cat_name] = [(cat_name, cat_url)]
                    
                except Exception as e:
                    logger.debug(f"Error procesando elemento de menú: {e}")
            
            # Si no encontramos suficientes categorías, buscar alternativas
            if len(categories) < 5:
                logger.info("⚠ Pocas categorías encontradas, buscando alternativas...")
                alt_links = await page.query_selector_all(
                    "a[href*='/categoria'], a[href*='/departamento'], a[href*='/seccion']"
                )
                
                for link in alt_links:
                    try:
                        text = await link.text_content()
                        href = await link.get_attribute("href")
                        
                        if text and href and 'venex.com.ar' in urljoin(self.base_url, href):
                            cat_name = text.strip()[:50]
                            cat_url = urljoin(self.base_url, href)
                            
                            if cat_name not in categories:
                                categories[cat_name] = [(cat_name, cat_url)]
                    except:
                        pass
            
            logger.info(f"✓ Total de categorías descubiertas: {len(categories)}")
            return categories
            
        except Exception as e:
            logger.error(f"✗ Error descubriendo categorías: {e}")
            return categories
    
    async def extract_price_robust(self, price_text: str) -> Optional[float]:
        """Extraer precio con limpieza robusta - evita números gigantes"""
        try:
            if not price_text:
                return None
            
            # Eliminar espacios en blanco
            price_text = price_text.strip()
            
            # Buscar patrón de precio: $ seguido de dígitos
            # Pueden haber miles separados por . o ,
            price_match = re.search(r'\$?\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{2})?)', price_text)
            
            if not price_match:
                return None
            
            price_str = price_match.group(1)
            
            # Detectar si usa punto o coma como separador de miles
            if price_str.count('.') > 1 or (price_str.count('.') == 1 and price_str.count(',') == 0):
                # Formato: 1.234.567,89 (Argentina)
                price_str = price_str.replace('.', '').replace(',', '.')
            elif price_str.count(',') > 1:
                # Formato anómalo, limpiar
                price_str = price_str.replace(',', '')
            else:
                # Formato: 1,234.56 o 1.234,56
                if price_str.endswith(',00') or price_str.endswith('.00'):
                    price_str = price_str[:-3]
                price_str = price_str.replace(',', '.')
            
            # Convertir a float
            price = float(price_str)
            
            # Validar rango sensato (> 100 y < 100 millones)
            if price < 100 or price > 100_000_000:
                logger.debug(f"Precio fuera de rango: {price}")
                return None
            
            return price
            
        except Exception as e:
            logger.debug(f"Error parseando precio '{price_text}': {e}")
            return None
    
    async def extract_image_url(self, page: Page, product_element) -> Optional[str]:
        """Extraer URL de imagen"""
        try:
            img = await product_element.query_selector("img")
            if not img:
                return None
            
            src = await img.get_attribute("src")
            if not src:
                src = await img.get_attribute("data-src")
            if not src:
                src = await img.get_attribute("data-original")
            
            if not src:
                return None
            
            # Filtrar placeholders
            if any(skip in src.lower() for skip in ['placeholder', 'loading', 'icon', 'logo', 'blank', 'default', 'no-image']):
                return None
            
            full_url = urljoin(self.base_url, src)
            return full_url
            
        except Exception as e:
            logger.debug(f"Error extrayendo imagen: {e}")
            return None
    
    async def extract_category_from_page(self, page: Page) -> Optional[Tuple[str, str]]:
        """Extraer categoría y subcategoría desde breadcrumb o URL"""
        try:
            # Intenta desde breadcrumb
            breadcrumb_selectors = [
                ".breadcrumb a:nth-last-child(2)",
                "[class*='breadcrumb'] a:nth-last-child(2)",
                ".breadcrumbs a:nth-last-child(2)"
            ]
            
            for selector in breadcrumb_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and text.strip():
                            return (text.strip(), None)
                except:
                    pass
            
            # Intenta desde la URL
            current_url = page.url
            parts = current_url.split('/')
            if len(parts) > 3:
                category = parts[-1].replace('-', ' ').title()
                return (category, None)
            
        except Exception as e:
            logger.debug(f"Error extrayendo categoría: {e}")
        
        return None
    
    async def extract_products_from_page(self, page: Page, category_name: str = "General") -> List[Dict[str, Any]]:
        """Extraer productos de la página actual"""
        products = []
        try:
            # Esperar productos
            try:
                await page.wait_for_selector("[class*='product'], [class*='item'], article", timeout=5000)
            except:
                logger.warning(f"⚠ No hay productos en {page.url}")
                return products
            
            # Selectores de productos
            product_selectors = [
                "[class*='product-card']",
                "[class*='product-item']",
                "[class*='item-card']",
                ".producto",
                ".product",
                "[data-product]",
                "article",
                "[class*='box-product']"
            ]
            
            product_elements = []
            for selector in product_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        product_elements = elements
                        logger.info(f"✓ {len(elements)} productos encontrados")
                        break
                except:
                    pass
            
            if not product_elements:
                return products
            
            for idx, product_el in enumerate(product_elements):
                try:
                    # Título
                    title = None
                    for sel in ["h2", "h3", "h4", ".title", ".name", "a"]:
                        try:
                            el = await product_el.query_selector(sel)
                            if el:
                                title = await el.text_content()
                                if title:
                                    break
                        except:
                            pass
                    
                    if not title or len(title.strip()) < 3:
                        continue
                    
                    title = title.strip()
                    title = re.sub(r'\s+', ' ', title)[:250]
                    
                    # Duplicados
                    norm_title = title.lower().strip()
                    if norm_title in self.seen_titles:
                        continue
                    self.seen_titles.add(norm_title)
                    
                    # Precio - CRÍTICO
                    price_text = None
                    price_selectors = [
                        "[class*='price']",
                        ".precio",
                        "span[class*='price']",
                        "[data-price]",
                        ".amount",
                        ".valor",
                        "[class*='valor']"
                    ]
                    
                    for sel in price_selectors:
                        try:
                            el = await product_el.query_selector(sel)
                            if el:
                                price_text = await el.text_content()
                                if price_text and '$' in price_text:
                                    break
                        except:
                            pass
                    
                    # Si no encontramos precio en selectores, buscar cualquier texto con $
                    if not price_text:
                        inner_text = await product_el.inner_text()
                        prices = re.findall(r'\$\s*[0-9,.]+', inner_text)
                        if prices:
                            price_text = prices[0]
                    
                    if not price_text:
                        continue
                    
                    cost = await self.extract_price_robust(price_text)
                    if cost is None:
                        continue
                    
                    # Precio venta
                    selling_price = round(cost * 1.15, 2)
                    
                    # Imagen
                    image_url = await self.extract_image_url(page, product_el)
                    
                    # Categoría
                    cat_info = await self.extract_category_from_page(page)
                    if cat_info:
                        category_name = cat_info[0]
                    
                    product = {
                        "titulo": title,
                        "categoria": category_name,
                        "precio_costo": cost,
                        "precio_venta": selling_price,
                        "imagen": image_url or "",
                        "stock": True
                    }
                    
                    products.append(product)
                    logger.info(f"✓ [{len(products)}] {title[:40]}... → ${selling_price}")
                    
                except Exception as e:
                    logger.debug(f"Error en producto {idx}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"✗ Error en extract_products_from_page: {e}")
        
        return products
    
    async def handle_pagination(self, page: Page, category: str) -> List[Dict[str, Any]]:
        """Manejar paginación"""
        all_products = []
        page_num = 1
        max_pages = 50
        
        try:
            while page_num <= max_pages:
                logger.info(f"📄 Página {page_num}")
                
                products = await self.extract_products_from_page(page, category)
                all_products.extend(products)
                
                if not products:
                    logger.info("ℹ Página vacía")
                    break
                
                # Siguiente página
                next_found = False
                try:
                    next_selectors = [
                        "a[class*='next']",
                        "a[aria-label*='next']",
                        ".pagination a[href]:last-child",
                        "a:contains('Siguiente')"
                    ]
                    
                    for selector in next_selectors:
                        links = await page.query_selector_all(selector)
                        for link in links:
                            try:
                                cls = await link.get_attribute("class")
                                if cls and "disabled" in cls:
                                    continue
                                
                                next_url = await link.get_attribute("href")
                                if next_url:
                                    full_url = urljoin(self.base_url, next_url)
                                    if await self.goto_page(page, full_url, wait_time=2000):
                                        page_num += 1
                                        next_found = True
                                        break
                            except:
                                pass
                        
                        if next_found:
                            break
                except Exception as e:
                    logger.debug(f"Error buscando siguiente: {e}")
                
                if not next_found:
                    break
            
        except Exception as e:
            logger.error(f"✗ Error en handle_pagination: {e}")
        
        return all_products
    
    async def scrape_category(self, page: Page, category_name: str, category_url: str) -> List[Dict[str, Any]]:
        """Scrapear una categoría completa"""
        try:
            if category_url in self.visited_urls:
                return []
            
            self.visited_urls.add(category_url)
            logger.info(f"🔗 Scrapeando: {category_name}")
            
            if not await self.goto_page(page, category_url, wait_time=2500):
                return []
            
            products = await self.handle_pagination(page, category_name)
            
            logger.info(f"✓ {len(products)} productos de '{category_name}'")
            return products
            
        except Exception as e:
            logger.error(f"✗ Error en scrape_category: {e}")
            return []
    
    async def save_products(self, filename: str = "productos.json"):
        """Guardar productos"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=4)
            logger.info(f"✓ {len(self.products)} productos guardados en {filename}")
            return True
        except Exception as e:
            logger.error(f"✗ Error guardando: {e}")
            return False
    
    async def run(self):
        """Ejecutar scraper completo"""
        try:
            await self.init_browser()
            page = await self.context.new_page()
            
            logger.info("🚀 Iniciando scraper Venex...")
            
            # Descubrir categorías
            categories = await self.discover_categories_structure(page)
            
            if not categories:
                logger.warning("⚠ No se descubrieron categorías")
                return 1
            
            logger.info(f"✓ {len(categories)} categorías descubiertas\n")
            
            # Scrapear cada categoría
            for idx, (cat_name, cat_urls) in enumerate(categories.items(), 1):
                logger.info(f"\n{'='*60}")
                logger.info(f"[{idx}/{len(categories)}] Categoría: {cat_name}")
                logger.info(f"{'='*60}")
                
                try:
                    for subcategory_name, subcategory_url in cat_urls:
                        products = await self.scrape_category(
                            page, 
                            subcategory_name, 
                            subcategory_url
                        )
                        self.products.extend(products)
                except Exception as e:
                    logger.error(f"✗ Error procesando {cat_name}: {e}")
                    continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 RESUMEN FINAL")
            logger.info(f"{'='*60}")
            logger.info(f"Total de productos extraídos: {len(self.products)}")
            logger.info(f"Categorías únicas: {len(set(p.get('categoria', 'General') for p in self.products))}")
            
            # Guardar
            if await self.save_products():
                logger.info("✅ Scraping completado exitosamente")
                return 0
            else:
                return 1
            
        except Exception as e:
            logger.error(f"❌ Error fatal: {e}")
            return 1
        finally:
            await self.close_browser()


async def main():
    """Punto de entrada"""
    scraper = VenexScraper()
    return await scraper.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
