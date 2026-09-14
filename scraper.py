#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Scraper para Venex (https://www.venex.com.ar)
Descubre dinámicamente todas las categorías de productos y extrae el catálogo completo
con margen de ganancia del 15% (costo * 1.15)

Arquitectura:
- Descubrimiento dinámico de categorías y subcategorías
- Control inteligente de paginación
- Prevención de timeouts con domcontentloaded
- Extracción limpia de datos sin errores de sintaxis
- Consolidación en productos.json
"""

import asyncio
import json
import re
from typing import List, Set, Dict, Any, Optional
from urllib.parse import urljoin
import logging

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VenexScraper:
    """Web scraper completo para catálogo de productos de Venex"""
    
    def __init__(self):
        self.base_url = "https://www.venex.com.ar"
        self.products: List[Dict[str, Any]] = []
        self.seen_titles: Set[str] = set()
        self.visited_urls: Set[str] = set()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
    async def init_browser(self):
        """Inicializar navegador Playwright"""
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
        """Cerrar recursos del navegador"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("✓ Navegador cerrado")
        except Exception as e:
            logger.error(f"✗ Error cerrando navegador: {e}")
        
    async def goto_page(self, page: Page, url: str, wait_time: int = 3000) -> bool:
        """Navegar a URL con manejo robusto de errores"""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(wait_time)
            return True
        except Exception as e:
            logger.error(f"✗ Fallo navegando a {url}: {e}")
            return False
            
    async def discover_categories(self, page: Page) -> List[str]:
        """Descubrir dinámicamente todas las URLs de categorías desde navegación principal"""
        category_urls = []
        try:
            if not await self.goto_page(page, self.base_url, wait_time=2000):
                logger.warning("✗ No se pudo acceder a la página principal")
                return category_urls
            
            # Intenta encontrar menú de navegación y extractar enlaces de categorías
            try:
                category_links = await page.query_selector_all(
                    "nav a, .menu a, .navbar a, [class*='category'] a, [class*='menu'] a, [class*='nav'] a"
                )
                
                for link in category_links:
                    try:
                        href = await link.get_attribute("href")
                        text = await link.text_content()
                        
                        if href and text and not href.startswith("#") and "javascript:" not in href:
                            full_url = urljoin(self.base_url, href)
                            if "venex.com.ar" in full_url and full_url not in self.visited_urls:
                                category_urls.append(full_url)
                                logger.info(f"✓ Categoría descubierta: {text.strip()}")
                    except Exception as e:
                        logger.debug(f"Error extrayendo enlace de categoría: {e}")
                        
            except Exception as e:
                logger.warning(f"✗ No se encontraron elementos de navegación: {e}")
            
            # Selectores alternativos si no se encuentran categorías
            if not category_urls:
                logger.info("⚠ Intentando selectores alternativos...")
                alt_patterns = [
                    "a[href*='/categoria']",
                    "a[href*='/departamento']",
                    "a[href*='/productos']",
                    "a[href*='/seccion']"
                ]
                
                for pattern in alt_patterns:
                    try:
                        alt_links = await page.query_selector_all(pattern)
                        for link in alt_links:
                            try:
                                href = await link.get_attribute("href")
                                if href and href not in category_urls:
                                    full_url = urljoin(self.base_url, href)
                                    if full_url not in category_urls:
                                        category_urls.append(full_url)
                            except:
                                pass
                    except:
                        pass
            
            # Eliminar duplicados
            category_urls = list(set(category_urls))
            logger.info(f"✓ Total de categorías descubiertas: {len(category_urls)}")
            
        except Exception as e:
            logger.error(f"✗ Error descubriendo categorías: {e}")
            
        return category_urls
        
    async def extract_price(self, price_text: str) -> Optional[float]:
        """Extraer y convertir precio desde texto"""
        try:
            if not price_text:
                return None
                
            # Eliminar símbolos de moneda y espacios
            cleaned = re.sub(r'[$\s]', '', price_text)
            # Eliminar separador de miles (punto en formato Argentina)
            cleaned = re.sub(r'\.(?=\d{3})', '', cleaned)
            # Reemplazar coma con punto para decimal
            cleaned = cleaned.replace(',', '.')
            
            price = float(cleaned)
            
            # Descartar precios menores a 100
            if price < 100:
                return None
                
            return price
        except (ValueError, AttributeError) as e:
            logger.debug(f"No se pudo parsear precio '{price_text}': {e}")
            return None
            
    async def extract_image_url(self, page: Page, product_element) -> Optional[str]:
        """Extraer URL absoluta de imagen desde elemento de producto"""
        try:
            # Buscar tag img
            img = await product_element.query_selector("img")
            if not img:
                return None
                
            # Intentar atributo src primero
            src = await img.get_attribute("src")
            if not src:
                src = await img.get_attribute("data-src")
            if not src:
                src = await img.get_attribute("data-original")
                
            if not src:
                return None
                
            # Saltar placeholders e imágenes institucionales
            if any(skip in src.lower() for skip in ['placeholder', 'loading', 'icon', 'logo', 'blank', 'default']):
                return None
                
            # Convertir a URL absoluta
            full_url = urljoin(self.base_url, src)
            return full_url
            
        except Exception as e:
            logger.debug(f"Error extrayendo imagen: {e}")
            return None
            
    async def extract_category_from_breadcrumb(self, page: Page) -> Optional[str]:
        """Extraer categoría desde migas de pan (breadcrumb)"""
        try:
            breadcrumb_selectors = [
                ".breadcrumb a:nth-last-child(2)",
                "[class*='breadcrumb'] a:nth-last-child(2)",
                ".breadcrumb .active",
                "[aria-label='breadcrumb'] li:nth-last-child(2) a",
                ".breadcrumbs a:nth-last-child(2)"
            ]
            
            for selector in breadcrumb_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and text.strip():
                            return text.strip()
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"Error extrayendo breadcrumb: {e}")
            
        return None
        
    async def extract_products_from_page(self, page: Page, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extraer todos los productos de la página actual"""
        products = []
        try:
            # Esperar a que carguen productos
            try:
                await page.wait_for_selector("[class*='product'], [class*='item'], article", timeout=5000)
            except:
                logger.warning("⚠ No se encontraron productos en la página")
                return products
                
            # Múltiples selectores de productos
            product_selectors = [
                "[class*='product-card']",
                "[class*='product-item']",
                "[class*='item-card']",
                ".producto",
                ".product",
                "[data-product]",
                "article",
                "[class*='box-product']",
                "[class*='item']"
            ]
            
            product_elements = []
            for selector in product_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        product_elements = elements
                        logger.info(f"✓ Encontrados {len(elements)} productos con selector: {selector}")
                        break
                except:
                    continue
                    
            if not product_elements:
                logger.warning("⚠ No se pudieron encontrar elementos de producto")
                return products
                
            for product_el in product_elements:
                try:
                    # Extraer título
                    title_selectors = ["h2", "h3", "h4", ".title", "[class*='title']", ".name", "[class*='name']", "a"]
                    title = None
                    
                    for sel in title_selectors:
                        try:
                            el = await product_el.query_selector(sel)
                            if el:
                                title = await el.text_content()
                                if title:
                                    break
                        except:
                            continue
                            
                    if not title:
                        continue
                        
                    # Limpiar título
                    title = title.strip()
                    title = re.sub(r'\s+', ' ', title)
                    title = title[:200]  # Limitar longitud
                    
                    if len(title) < 3:
                        continue
                    
                    # Verificar duplicados
                    normalized_title = title.lower().strip()
                    if normalized_title in self.seen_titles:
                        continue
                        
                    self.seen_titles.add(normalized_title)
                    
                    # Extraer precio
                    price_selectors = [
                        "[class*='price']",
                        ".precio",
                        "span[class*='price']",
                        "[data-price]",
                        ".amount"
                    ]
                    price_text = None
                    
                    for sel in price_selectors:
                        try:
                            el = await product_el.query_selector(sel)
                            if el:
                                price_text = await el.text_content()
                                if price_text:
                                    break
                        except:
                            continue
                            
                    cost = None
                    if price_text:
                        cost = await self.extract_price(price_text)
                        
                    if cost is None:
                        continue
                        
                    # Calcular precio de venta (margen 15%)
                    selling_price = round(cost * 1.15, 2)
                    
                    # Extraer imagen
                    image_url = await self.extract_image_url(page, product_el)
                    
                    # Extraer categoría si no se proporcionó
                    if not category:
                        category = await self.extract_category_from_breadcrumb(page)
                        
                    product = {
                        "titulo": title,
                        "categoria": category or "General",
                        "precio_costo": cost,
                        "precio_venta": selling_price,
                        "imagen": image_url or "",
                        "stock": True
                    }
                    
                    products.append(product)
                    logger.info(f"✓ Extraído: {title[:50]}... → ${selling_price}")
                    
                except Exception as e:
                    logger.debug(f"Error extrayendo producto: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"✗ Error en extract_products_from_page: {e}")
            
        return products
        
    async def handle_pagination(self, page: Page, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Manejar paginación y extraer productos de todas las páginas"""
        all_products = []
        page_num = 1
        max_pages = 50  # Límite de seguridad
        
        try:
            while page_num <= max_pages:
                logger.info(f"📄 Scrapeando página {page_num}")
                
                # Extraer productos de página actual
                products = await self.extract_products_from_page(page, category)
                all_products.extend(products)
                
                if not products:
                    logger.info("ℹ No se encontraron productos en esta página")
                    break
                
                # Verificar siguiente página
                next_page_found = False
                try:
                    # Múltiples selectores para siguiente página
                    next_selectors = [
                        "a[class*='next']",
                        "a[aria-label*='next']",
                        ".pagination a[href]:last-child",
                        "[class*='pagination'] a[class*='next']",
                        "a:contains('Siguiente')",
                        ".pagination li:last-child a"
                    ]
                    
                    next_link = None
                    for selector in next_selectors:
                        try:
                            links = await page.query_selector_all(selector)
                            for link in links:
                                try:
                                    # Verificar si está deshabilitado
                                    disabled = await link.get_attribute("class")
                                    if disabled and "disabled" in disabled:
                                        continue
                                    
                                    aria_disabled = await link.get_attribute("aria-disabled")
                                    if aria_disabled == "true":
                                        continue
                                        
                                    next_link = link
                                    break
                                except:
                                    pass
                            
                            if next_link:
                                break
                        except:
                            continue
                            
                    if next_link:
                        try:
                            next_url = await next_link.get_attribute("href")
                            if next_url:
                                full_url = urljoin(self.base_url, next_url)
                                if await self.goto_page(page, full_url, wait_time=2000):
                                    page_num += 1
                                    next_page_found = True
                                    await page.wait_for_timeout(1000)
                        except:
                            pass
                            
                except Exception as e:
                    logger.debug(f"Error buscando siguiente página: {e}")
                    
                if not next_page_found:
                    # Intentar scroll infinito
                    try:
                        old_height = await page.evaluate("document.body.scrollHeight")
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        new_height = await page.evaluate("document.body.scrollHeight")
                        
                        if new_height > old_height:
                            page_num += 1
                            new_products = await self.extract_products_from_page(page, category)
                            if new_products:
                                all_products.extend(new_products)
                                continue
                    except:
                        pass
                        
                    logger.info("✓ No hay más páginas")
                    break
                    
        except Exception as e:
            logger.error(f"✗ Error en handle_pagination: {e}")
            
        return all_products
        
    async def scrape_category(self, page: Page, category_url: str) -> List[Dict[str, Any]]:
        """Scrapear todos los productos de una categoría"""
        try:
            if category_url in self.visited_urls:
                logger.debug(f"⊘ URL ya visitada: {category_url}")
                return []
                
            self.visited_urls.add(category_url)
            logger.info(f"🔗 Scrapeando categoría: {category_url}")
            
            if not await self.goto_page(page, category_url, wait_time=2000):
                return []
                
            # Extraer nombre de categoría desde breadcrumb
            category_name = await self.extract_category_from_breadcrumb(page)
            
            # Extraer todos los productos con paginación
            products = await self.handle_pagination(page, category_name)
            
            logger.info(f"✓ Extraídos {len(products)} productos de {category_url[:60]}...")
            return products
            
        except Exception as e:
            logger.error(f"✗ Error scrapeando categoría {category_url}: {e}")
            return []
            
    async def save_products(self, filename: str = "productos.json"):
        """Guardar productos en archivo JSON"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=4)
            logger.info(f"✓ Guardados {len(self.products)} productos en {filename}")
            return True
        except Exception as e:
            logger.error(f"✗ Error guardando productos: {e}")
            return False
            
    async def run(self):
        """Método de ejecución principal"""
        try:
            await self.init_browser()
            page = await self.context.new_page()
            
            logger.info("🚀 Iniciando scraper de Venex...")
            
            # Descubrir categorías
            categories = await self.discover_categories(page)
            
            if not categories:
                logger.warning("⚠ No se descubrieron categorías, intentando scraping directo")
                products = await self.handle_pagination(page)
                self.products.extend(products)
            else:
                # Scrapear cada categoría
                for idx, category_url in enumerate(categories, 1):
                    logger.info(f"📊 Procesando categoría {idx}/{len(categories)}")
                    try:
                        products = await self.scrape_category(page, category_url)
                        self.products.extend(products)
                    except Exception as e:
                        logger.error(f"✗ Error procesando categoría {idx}: {e}")
                        continue
                    
            logger.info(f"📈 Total de productos extraídos: {len(self.products)}")
            
            # Guardar resultados
            if await self.save_products():
                logger.info("✅ Scraping completado exitosamente")
                return 0
            else:
                logger.error("❌ Error guardando resultados")
                return 1
            
        except Exception as e:
            logger.error(f"❌ Error fatal en scraper: {e}")
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
