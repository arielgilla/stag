#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Scraper mejorado para Venex (https://www.venex.com.ar)
Con descubrimiento automático de selectores y logging detallado
"""

import asyncio
import json
import re
import sys
from typing import List, Set, Dict, Any, Optional
from urllib.parse import urljoin
import logging
from datetime import datetime

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Configurar logging con archivo
log_file = f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class VenexScraperV2:
    """Web scraper mejorado para Venex"""
    
    def __init__(self):
        self.base_url = "https://www.venex.com.ar"
        self.products: List[Dict[str, Any]] = []
        self.seen_titles: Set[str] = set()
        self.visited_urls: Set[str] = set()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.discovered_selectors = {
            "product": None,
            "title": None,
            "price": None,
            "image": None
        }
        
    async def init_browser(self):
        """Inicializar navegador con opciones anti-detección"""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="es-AR",
                timezone_id="America/Argentina/Buenos_Aires"
            )
            logger.info("✓ Navegador inicializado correctamente")
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
        
    async def goto_page(self, page: Page, url: str, wait_time: int = 3000, retries: int = 3) -> bool:
        """Navegar a URL con reintentos"""
        for attempt in range(retries):
            try:
                logger.debug(f"Navegando a {url} (intento {attempt + 1}/{retries})")
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if response and response.status >= 400:
                    logger.warning(f"Código HTTP {response.status} para {url}")
                
                await page.wait_for_timeout(wait_time)
                
                # Verificar si Cloudflare bloqueó
                try:
                    await page.wait_for_selector("body", timeout=2000)
                    body_text = await page.content()
                    if "cf_challenge" in body_text or "Challenge" in body_text:
                        logger.warning(f"Cloudflare challenge detectado en {url}")
                        if attempt < retries - 1:
                            await page.wait_for_timeout(5000)
                            continue
                except:
                    pass
                
                logger.info(f"✓ Página cargada: {url}")
                return True
                
            except Exception as e:
                logger.debug(f"Error en intento {attempt + 1}: {e}")
                if attempt < retries - 1:
                    wait_time_retry = wait_time * (2 ** attempt)
                    logger.info(f"Esperando {wait_time_retry}ms antes de reintentar...")
                    await page.wait_for_timeout(wait_time_retry)
        
        logger.error(f"✗ Falló navegación a {url} después de {retries} intentos")
        return False
    
    async def discover_product_selectors(self, page: Page) -> bool:
        """Descubrir automáticamente los selectores de productos"""
        try:
            logger.info("🔍 Descubriendo selectores de productos...")
            
            # Lista de selectores candidatos comunes
            product_selectors = [
                "[class*='product']",
                "[class*='item']",
                "[class*='card']",
                "[class*='article']",
                "article",
                "[data-product]",
                ".producto",
                ".product",
                ".item",
                "[role='option']"
            ]
            
            for selector in product_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if len(elements) > 0:
                        logger.debug(f"Encontrados {len(elements)} elementos con '{selector}'")
                        
                        # Verificar que tengan contenido
                        first_element = elements[0]
                        text_content = await first_element.inner_text()
                        
                        if text_content and len(text_content) > 20:
                            logger.info(f"✓ Selector de producto identificado: '{selector}' ({len(elements)} elementos)")
                            self.discovered_selectors["product"] = selector
                            break
                except Exception as e:
                    logger.debug(f"Error probando selector '{selector}': {e}")
            
            if not self.discovered_selectors["product"]:
                logger.warning("⚠ No se encontró selector de producto válido")
                return False
            
            # Descubrir selectores de título
            first_product = await page.query_selector(self.discovered_selectors["product"])
            if first_product:
                title_selectors = ["h1", "h2", "h3", "h4", ".title", ".name", ".producto-titulo", "a"]
                for selector in title_selectors:
                    try:
                        el = await first_product.query_selector(selector)
                        if el:
                            text = await el.inner_text()
                            if text and len(text) > 3:
                                logger.info(f"✓ Selector de título: '{selector}'")
                                self.discovered_selectors["title"] = selector
                                break
                    except:
                        pass
                
                # Descubrir selectores de precio
                price_selectors = [
                    "[class*='price']",
                    ".precio",
                    "[class*='valor']",
                    "[class*='amount']",
                    ".monto",
                    "[data-price]"
                ]
                for selector in price_selectors:
                    try:
                        el = await first_product.query_selector(selector)
                        if el:
                            text = await el.inner_text()
                            if text and '$' in text:
                                logger.info(f"✓ Selector de precio: '{selector}'")
                                self.discovered_selectors["price"] = selector
                                break
                    except:
                        pass
                
                # Descubrir selectores de imagen
                image_selectors = ["img", "[class*='image'] img", "[class*='thumb'] img"]
                for selector in image_selectors:
                    try:
                        el = await first_product.query_selector(selector)
                        if el:
                            src = await el.get_attribute("src")
                            if src:
                                logger.info(f"✓ Selector de imagen: '{selector}'")
                                self.discovered_selectors["image"] = selector
                                break
                    except:
                        pass
            
            return bool(self.discovered_selectors["product"])
            
        except Exception as e:
            logger.error(f"✗ Error descubriendo selectores: {e}")
            return False
    
    async def extract_price_robust(self, price_text: str) -> Optional[float]:
        """Extraer precio de forma robusta"""
        try:
            if not price_text:
                return None
            
            price_text = price_text.strip()
            logger.debug(f"Extrayendo precio de: '{price_text}'")
            
            # Buscar patrón: $ seguido de números
            price_match = re.search(r'\$?\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)', price_text)
            
            if not price_match:
                logger.debug(f"No se encontró patrón de precio en '{price_text}'")
                return None
            
            price_str = price_match.group(1)
            logger.debug(f"Patrón encontrado: '{price_str}'")
            
            # Limpiar formato argentino
            # Detectar: 1.234.567,89 o 1234567,89
            dots = price_str.count('.')
            commas = price_str.count(',')
            
            if dots > 1 or (dots == 1 and commas == 0 and not price_str.endswith('.00')):
                # Múltiples puntos = separadores de miles (Argentina)
                price_str = price_str.replace('.', '').replace(',', '.')
            elif commas > 1:
                # Múltiples comas - formato raro
                price_str = re.sub(r'[,.]', '', price_str)
            elif commas == 1 and dots == 0:
                # Una coma, sin puntos - probablemente decimal
                if price_str.index(',') >= len(price_str) - 3:
                    price_str = price_str.replace(',', '.')
                else:
                    price_str = price_str.replace(',', '')
            
            price = float(price_str)
            
            # Validar rango (100 a 50 millones)
            if price < 100 or price > 50_000_000:
                logger.debug(f"Precio fuera de rango válido: {price}")
                return None
            
            logger.debug(f"Precio extraído correctamente: {price}")
            return price
            
        except Exception as e:
            logger.debug(f"Error parseando precio: {e}")
            return None
    
    async def extract_products_from_page(self, page: Page, category_name: str = "General") -> List[Dict[str, Any]]:
        """Extraer productos usando selectores descubiertos"""
        products = []
        try:
            if not self.discovered_selectors["product"]:
                logger.warning("⚠ Selectores no inicializados, descubriendo...")
                if not await self.discover_product_selectors(page):
                    return products
            
            # Obtener todos los productos
            product_elements = await page.query_selector_all(self.discovered_selectors["product"])
            logger.info(f"Encontrados {len(product_elements)} productos en la página")
            
            if not product_elements:
                return products
            
            for idx, product_el in enumerate(product_elements):
                try:
                    # Extraer título
                    title = None
                    if self.discovered_selectors["title"]:
                        try:
                            el = await product_el.query_selector(self.discovered_selectors["title"])
                            if el:
                                title = await el.inner_text()
                        except:
                            pass
                    
                    # Fallback si no se encontró
                    if not title:
                        for sel in ["h2", "h3", "a", "span"]:
                            try:
                                el = await product_el.query_selector(sel)
                                if el:
                                    title = await el.inner_text()
                                    if title and len(title) > 5:
                                        break
                            except:
                                pass
                    
                    if not title or len(title.strip()) < 3:
                        continue
                    
                    title = title.strip()
                    title = re.sub(r'\s+', ' ', title)[:250]
                    
                    # Verificar duplicados
                    norm_title = title.lower().strip()
                    if norm_title in self.seen_titles:
                        continue
                    self.seen_titles.add(norm_title)
                    
                    # Extraer precio
                    price_text = None
                    if self.discovered_selectors["price"]:
                        try:
                            el = await product_el.query_selector(self.discovered_selectors["price"])
                            if el:
                                price_text = await el.inner_text()
                        except:
                            pass
                    
                    # Fallback: buscar en todo el texto
                    if not price_text:
                        inner_text = await product_el.inner_text()
                        prices = re.findall(r'\$\s*[0-9.,]+', inner_text)
                        if prices:
                            price_text = prices[0]
                    
                    if not price_text:
                        logger.debug(f"No se encontró precio para: {title[:30]}")
                        continue
                    
                    cost = await self.extract_price_robust(price_text)
                    if cost is None:
                        continue
                    
                    # Calcular precio de venta
                    selling_price = round(cost * 1.15, 2)
                    
                    # Extraer imagen
                    image_url = ""
                    if self.discovered_selectors["image"]:
                        try:
                            el = await product_el.query_selector(self.discovered_selectors["image"])
                            if el:
                                src = await el.get_attribute("src") or await el.get_attribute("data-src")
                                if src and 'placeholder' not in src.lower():
                                    image_url = urljoin(self.base_url, src)
                        except:
                            pass
                    
                    product = {
                        "titulo": title,
                        "categoria": category_name,
                        "precio_costo": cost,
                        "precio_venta": selling_price,
                        "imagen": image_url,
                        "stock": True
                    }
                    
                    products.append(product)
                    logger.info(f"✓ [{len(products)}] {title[:40]}... | ${cost} → ${selling_price}")
                    
                except Exception as e:
                    logger.debug(f"Error extrayendo producto {idx}: {e}")
                    continue
            
            logger.info(f"✓ Extraídos {len(products)} productos de esta página")
            return products
            
        except Exception as e:
            logger.error(f"✗ Error en extract_products_from_page: {e}")
            return products
    
    async def handle_pagination(self, page: Page, category: str) -> List[Dict[str, Any]]:
        """Manejar paginación"""
        all_products = []
        page_num = 1
        max_pages = 100
        
        try:
            while page_num <= max_pages:
                logger.info(f"\n📄 ===== PÁGINA {page_num} =====")
                
                products = await self.extract_products_from_page(page, category)
                all_products.extend(products)
                
                if not products:
                    logger.info("ℹ Página vacía, deteniendo paginación")
                    break
                
                # Buscar siguiente página
                next_found = False
                try:
                    # Múltiples estrategias para encontrar siguiente
                    next_element = None
                    
                    # Estrategia 1: Buscar botón "Siguiente" o "Next"
                    for text_pattern in ['siguiente', 'next', '>', '→']:
                        try:
                            elements = await page.query_selector_all("a, button")
                            for el in elements:
                                text = await el.inner_text()
                                if text_pattern.lower() in text.lower():
                                    cls = await el.get_attribute("class") or ""
                                    if "disabled" not in cls.lower():
                                        next_element = el
                                        break
                            if next_element:
                                break
                        except:
                            pass
                    
                    # Estrategia 2: Selectores típicos de paginación
                    if not next_element:
                        pagination_selectors = [
                            ".pagination a[aria-label*='next']",
                            ".pagination a:not([class*='disabled']):last-child",
                            "[rel='next']",
                            "a[href*='page=']:last-child"
                        ]
                        for selector in pagination_selectors:
                            try:
                                el = await page.query_selector(selector)
                                if el:
                                    next_element = el
                                    break
                            except:
                                pass
                    
                    if next_element:
                        href = await next_element.get_attribute("href")
                        if href:
                            full_url = urljoin(self.base_url, href)
                            logger.info(f"Siguiente página encontrada: {full_url}")
                            if await self.goto_page(page, full_url, wait_time=2000):
                                page_num += 1
                                next_found = True
                                await page.wait_for_timeout(1000)
                
                except Exception as e:
                    logger.debug(f"Error buscando siguiente página: {e}")
                
                if not next_found:
                    logger.info("✓ No hay más páginas")
                    break
            
        except Exception as e:
            logger.error(f"✗ Error en handle_pagination: {e}")
        
        return all_products
    
    async def scrape_category(self, page: Page, category_url: str) -> List[Dict[str, Any]]:
        """Scrapear una categoría"""
        try:
            if category_url in self.visited_urls:
                logger.debug(f"⊘ URL ya visitada: {category_url}")
                return []
            
            self.visited_urls.add(category_url)
            
            # Extraer nombre de categoría de la URL
            category_name = category_url.split('/')[-1].replace('-', ' ').title()
            
            logger.info(f"\n{'='*70}")
            logger.info(f"🔗 SCRAPEANDO CATEGORÍA: {category_name}")
            logger.info(f"   URL: {category_url}")
            logger.info(f"{'='*70}")
            
            if not await self.goto_page(page, category_url, wait_time=2500):
                return []
            
            # Descubrir selectores en esta página
            if not await self.discover_product_selectors(page):
                logger.warning(f"⚠ No se encontraron productos en {category_name}")
                return []
            
            # Extraer productos con paginación
            products = await self.handle_pagination(page, category_name)
            
            logger.info(f"✓ Total de {len(products)} productos en {category_name}")
            return products
            
        except Exception as e:
            logger.error(f"✗ Error scrapeando categoría: {e}")
            return []
    
    async def discover_categories(self, page: Page) -> List[str]:
        """Descubrir todas las categorías del sitio"""
        categories = []
        try:
            logger.info("🔍 Descubriendo categorías...")
            
            if not await self.goto_page(page, self.base_url, wait_time=2000):
                logger.error("✗ No se pudo acceder a la página principal")
                return categories
            
            # Intentar múltiples estrategias
            selectors = [
                "nav a, .navbar a, .menu a, [class*='nav'] a",
                "a[href*='categoria'], a[href*='departamento'], a[href*='seccion']",
                "header a, [role='navigation'] a"
            ]
            
            found_categories = []
            for selector in selectors:
                try:
                    links = await page.query_selector_all(selector)
                    for link in links:
                        try:
                            href = await link.get_attribute("href")
                            text = await link.inner_text()
                            
                            if href and text and "venex.com.ar" in href and not href.startswith("#"):
                                if len(text.strip()) > 2 and len(text) < 100:
                                    full_url = urljoin(self.base_url, href)
                                    if full_url not in found_categories:
                                        found_categories.append(full_url)
                                        logger.debug(f"  - {text.strip()}: {full_url}")
                        except:
                            pass
                except:
                    pass
            
            # Remover duplicados
            categories = list(set(found_categories))
            logger.info(f"✓ Descubiertas {len(categories)} categorías")
            
            return categories
            
        except Exception as e:
            logger.error(f"✗ Error descubriendo categorías: {e}")
            return categories
    
    async def save_products(self, filename: str = "productos.json"):
        """Guardar productos en JSON"""
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
            
            logger.info(f"\n{'='*70}")
            logger.info(f"🚀 INICIANDO SCRAPER VENEX V2")
            logger.info(f"   Tiempo: {datetime.now().isoformat()}")
            logger.info(f"   URL Base: {self.base_url}")
            logger.info(f"{'='*70}\n")
            
            # Descubrir categorías
            categories = await self.discover_categories(page)
            
            if not categories:
                logger.warning("⚠ No se descubrieron categorías, intentando scraping de página principal")
                await self.goto_page(page, self.base_url)
                await self.discover_product_selectors(page)
                products = await self.handle_pagination(page, "General")
                self.products.extend(products)
            else:
                # Scrapear cada categoría
                for idx, category_url in enumerate(categories, 1):
                    try:
                        products = await self.scrape_category(page, category_url)
                        self.products.extend(products)
                    except Exception as e:
                        logger.error(f"✗ Error procesando categoría: {e}")
                        continue
            
            # Resumen final
            logger.info(f"\n{'='*70}")
            logger.info(f"📊 RESUMEN FINAL")
            logger.info(f"{'='*70}")
            logger.info(f"Total de productos: {len(self.products)}")
            logger.info(f"Categorías únicas: {len(set(p.get('categoria', 'General') for p in self.products))}")
            
            # Guardar
            if await self.save_products():
                logger.info(f"✅ SCRAPING COMPLETADO EXITOSAMENTE")
                logger.info(f"   Archivo: productos.json")
                logger.info(f"   Logs: {log_file}")
                return 0
            else:
                return 1
            
        except Exception as e:
            logger.error(f"❌ ERROR FATAL: {e}", exc_info=True)
            return 1
        finally:
            await self.close_browser()


async def main():
    """Punto de entrada"""
    scraper = VenexScraperV2()
    return await scraper.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    logger.info(f"\n{'='*70}")
    logger.info(f"CÓDIGO DE SALIDA: {exit_code}")
    logger.info(f"{'='*70}\n")
    exit(exit_code)
