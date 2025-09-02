from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time
import re
import requests
import os
from geopy.distance import geodesic

class PeerspaceListingScraper:
    def __init__(self, headless=False):
        self.target_location = (34.0627, -118.1834)  # 5464 E Valley Blvd
        self.max_distance = 5  # miles
        self.venues_data = []
        self.driver = None
        self.headless = headless
        
    def setup_driver(self):
        """Set up Chrome driver"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Stealth settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✅ Chrome driver ready")
            return True
        except Exception as e:
            print(f"❌ Chrome setup failed: {e}")
            return False

    def click_view_all_photos_button(self):
        """Click the 'View all' button to open full photo gallery"""
        try:
            print("🔍 Looking for 'View all' photos button...")
            
            # Multiple ways to find the button
            button_selectors = [
                '[data-testing-id="photoWithViewAllButton"]',  # Your exact data attribute
                'div[class*="tw-absolute"] span[data-testing-id="photoWithViewAllButton"]',
                'span[data-testing-id="photoWithViewAllButton"]',
            ]
            
            # Also try XPath for text-based search
            xpath_selectors = [
                "//*[contains(text(), 'View all')]",
                "//span[contains(text(), 'View all')]",
                "//div[contains(text(), 'View all')]"
            ]
            
            # Try CSS selectors first
            for selector in button_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"✅ Found 'View all' button with: {selector}")
                    
                    # Scroll button into view and click
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)
                    
                    # Try clicking
                    button.click()
                    print("✅ Clicked 'View all' button!")
                    time.sleep(3)  # Wait for gallery to open
                    return True
                    
                except Exception as e:
                    continue
            
            # Try XPath selectors
            for xpath in xpath_selectors:
                try:
                    button = self.driver.find_element(By.XPATH, xpath)
                    print(f"✅ Found 'View all' button with XPath")
                    
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)
                    button.click()
                    print("✅ Clicked 'View all' button!")
                    time.sleep(3)
                    return True
                    
                except Exception as e:
                    continue
            
            print("❌ Could not find 'View all' button")
            return False
            
        except Exception as e:
            print(f"❌ Error clicking view all button: {e}")
            return False

    def get_gallery_photos_after_click(self):
        """Get photos from the opened gallery modal"""
        try:
            print("📸 Extracting photos from opened gallery...")
            
            # After clicking "View all", photos might be in a modal/overlay
            gallery_modal_selectors = [
                '.modal img',
                '.overlay img', 
                '.gallery-modal img',
                '.lightbox img',
                '[role="dialog"] img',
                '.tw-fixed img',  # Tailwind fixed positioning (modal)
                'div[class*="tw-fixed"] img',
                '.carousel img',
                '.slider img'
            ]
            
            venue_photos = []
            
            for selector in gallery_modal_selectors:
                try:
                    images = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if images:
                        print(f"🎯 Found {len(images)} images in modal: {selector}")
                        
                        for img in images:
                            src = img.get_attribute('src')
                            if src and self.is_venue_photo_in_modal(src, img):
                                venue_photos.append(src)
                        
                        if venue_photos:
                            break  # Use first working modal selector
                            
                except:
                    continue
            
            # If no modal photos, try original button method
            if not venue_photos:
                print("📸 No modal photos, trying button images...")
                button_images = self.driver.find_elements(By.CSS_SELECTOR, 'button[class*="tw-aspect"] img')
                
                for img in button_images:
                    src = img.get_attribute('src')
                    if src and self.is_venue_photo_in_modal(src, img):
                        venue_photos.append(src)
            
            unique_photos = list(set(venue_photos))
            print(f"📷 Total venue photos collected: {len(unique_photos)}")
            return unique_photos
            
        except Exception as e:
            print(f"❌ Gallery extraction error: {e}")
            return []

    def is_venue_photo_in_modal(self, src, img_element):
        """Check if image in modal/gallery is a venue photo"""
        try:
            # Skip tiny images
            width = img_element.size['width']
            height = img_element.size['height']
            
            if width < 150 or height < 100:
                return False
            
            # Skip non-venue images
            skip_patterns = ['logo', 'icon', 'avatar', 'star', 'heart', 'arrow', 'close', 'x.svg']
            src_lower = src.lower()
            
            return not any(pattern in src_lower for pattern in skip_patterns)
            
        except:
            return True

    def get_photos_with_view_all_click(self):
        """Main photo extraction with 'View all' button click"""
        try:
            # Step 1: Try to click "View all" button
            view_all_clicked = self.click_view_all_photos_button()
            
            # Step 2: Extract photos (from modal if opened, or from page)
            if view_all_clicked:
                photos = self.get_gallery_photos_after_click()
            else:
                print("📸 No 'View all' button found, trying direct photo extraction...")
                photos = self.get_venue_photos_real_selectors()
            
            return photos
            
        except Exception as e:
            print(f"❌ Photo extraction failed: {e}")
            return []

    def get_venue_photos_real_selectors(self):
        """Use the REAL selectors you discovered"""
        try:
            venue_photos = []
            
            # Your discovered pattern - photos in buttons
            real_selectors = [
                'button[class*="tw-aspect"] img',  # General pattern
                'button span img',  # Simplified version
                'button img'  # Even simpler
            ]
            
            for selector in real_selectors:
                try:
                    print(f"🔍 Trying selector: {selector}")
                    images = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if images:
                        print(f"✅ Found {len(images)} images with: {selector}")
                        
                        for img in images:
                            src = img.get_attribute('src')
                            if src and self.is_high_quality_venue_photo(src, img):
                                venue_photos.append(src)
                        
                        break  # Use first working selector
                        
                except Exception as e:
                    print(f"❌ Selector failed: {selector} - {e}")
                    continue
            
            # Remove duplicates
            unique_photos = list(set(venue_photos))
            print(f"📷 Found {len(unique_photos)} unique venue photos")
            
            return unique_photos
            
        except Exception as e:
            print(f"❌ Photo extraction error: {e}")
            return []

    def is_high_quality_venue_photo(self, src, img_element):
        """Better photo filtering using your insights"""
        try:
            # Get actual displayed size
            width = img_element.size['width']
            height = img_element.size['height']
            
            # Skip tiny images (likely icons/logos)
            if width < 100 or height < 100:
                return False
            
            # Skip obvious non-venue images
            skip_keywords = ['logo', 'icon', 'avatar', 'profile', 'star', 'heart']
            src_lower = src.lower()
            
            if any(keyword in src_lower for keyword in skip_keywords):
                return False
            
            # Check if parent button suggests it's a gallery image
            try:
                parent_button = img_element.find_element(By.XPATH, "./..")  # Parent element
                parent_class = parent_button.get_attribute('class') or ""
                
                # Good signs it's a gallery photo
                if any(keyword in parent_class.lower() for keyword in ['aspect', 'gallery', 'carousel']):
                    return True
            except:
                pass
            
            # If reasonably large, probably a venue photo
            return width >= 200 and height >= 150
            
        except:
            return True  # When in doubt, include it

    def scrape_single_listing(self, listing_url):
        """Scrape one listing page - perfect for testing"""
        try:
            print(f"🏠 Loading: {listing_url}")
            self.driver.get(listing_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Extract all the data
            venue_data = {
                'url': listing_url,
                'name': self.find_text_by_multiple_selectors([
                    'h1',
                    '[data-testid*="title"]',
                    '.listing-title',
                    '.space-title'
                ]),
                'price_per_hour': self.extract_price_from_page(),
                'capacity': self.extract_capacity_from_page(),
                'address': self.find_text_by_multiple_selectors([
                    '.location-text',
                    '.neighborhood',
                    '[class*="address"]',
                    '[class*="location"]',
                    'span:contains("Los Angeles")',
                    'div:contains("CA")'
                ]),
                'category': self.find_text_by_multiple_selectors([
                    '.space-type',
                    '.listing-type', 
                    '[class*="category"]',
                    '.tag',
                    '.badge',
                    'span[class*="type"]'
                ]),
                'description': self.get_description(),
                'amenities': self.get_amenities(),
                'photos': self.get_photos_with_view_all_click(),
                'host_name': self.find_text_by_multiple_selectors([
                    '[data-testid*="host"]',
                    '.host-name',
                    '[class*="host"]'
                ]),
                'raw_page_text': self.driver.find_element(By.TAG_NAME, "body").text[:500]  # For debugging
            }
            
            venue_data['photo_count'] = len(venue_data['photos'])
            
            # Optionally download photos
            if venue_data['photos']:
                download_choice = input(f"Download {len(venue_data['photos'])} photos for '{venue_data['name']}'? (y/n): ")
                if download_choice.lower() == 'y':
                    self.download_venue_photos(venue_data['photos'], venue_data['name'])
            
            print(f"✅ Scraped: {venue_data['name']}")
            print(f"   Price: ${venue_data['price_per_hour']}/hr")
            print(f"   Capacity: {venue_data['capacity']} people")
            print(f"   Photos: {venue_data['photo_count']} images")
            
            return venue_data
            
        except Exception as e:
            print(f"❌ Error scraping {listing_url}: {e}")
            return None

    def find_text_by_multiple_selectors(self, selectors):
        """Try multiple CSS selectors until one works"""
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip()
                if text:
                    print(f"✅ Found with selector '{selector}': {text[:50]}")
                    return text
            except:
                continue
        
        print(f"❌ No text found with any selector: {selectors}")
        return "Not found"

    def extract_price_from_page(self):
        """Look for any dollar amounts on the page"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for common price patterns
            price_patterns = [
                r'\$(\d+)(?:/hour|/hr|per hour)',
                r'\$(\d+)',  # Any dollar amount
                r'(\d+)\s*(?:USD|dollars?)(?:/hour|/hr|per hour)?'
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    price = int(match)
                    if 10 <= price <= 2000:  # Reasonable hourly rate
                        print(f"💰 Found price: ${price}")
                        return price
            
            print("❌ No price found")
            return None
        except:
            return None

    def extract_capacity_from_page(self):
        """Look for capacity info"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            capacity_patterns = [
                r'up to (\d+) (?:people|guests)',
                r'capacity:?\s*(\d+)',
                r'(\d+)\s*(?:people|guests|persons)'
            ]
            
            for pattern in capacity_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    capacity = int(match)
                    if 1 <= capacity <= 500:
                        print(f"👥 Found capacity: {capacity}")
                        return capacity
            
            print("❌ No capacity found")
            return None
        except:
            return None

    def get_description(self):
        """Get venue description"""
        desc_selectors = [
            '[data-testid*="description"]',
            '.description',
            '.about',
            '.details p',
            'p'
        ]
        
        for selector in desc_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if len(text) > 50:  # Substantial description
                        return text[:300]  # First 300 chars
            except:
                continue
        
        return "No description found"

    def get_amenities(self):
        """Find amenities/features list"""
        amenities = []
        
        amenity_selectors = [
            '.amenity',
            '.feature',
            '.amenities li',
            '[data-testid*="amenity"]',
            '.facilities li',
            'li'
        ]
        
        for selector in amenity_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and 3 <= len(text) <= 50:  # Reasonable amenity length
                        amenities.append(text)
            except:
                continue
        
        return list(set(amenities))[:10]  # First 10 unique amenities

    def download_venue_photos(self, photo_urls, venue_name):
        """Download photos with better naming"""
        if not photo_urls:
            print("No photos to download")
            return
        
        # Create clean folder name
        safe_name = re.sub(r'[^\w\s-]', '', venue_name)[:30].strip()
        folder_name = f"venue_photos_{safe_name}"
        os.makedirs(folder_name, exist_ok=True)
        
        print(f"📁 Downloading {len(photo_urls)} photos to: {folder_name}")
        
        for i, url in enumerate(photo_urls):
            try:
                # Get high-res version of image
                clean_url = self.get_high_res_url(url)
                
                response = requests.get(clean_url, timeout=15)
                if response.status_code == 200:
                    # Better filename
                    ext = '.jpg'
                    if '.' in clean_url:
                        ext = '.' + clean_url.split('.')[-1].split('?')[0]
                    
                    filename = f"{folder_name}/{safe_name}_photo_{i+1:02d}{ext}"
                    
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ Downloaded: {filename}")
                else:
                    print(f"❌ Failed download {i+1}: Status {response.status_code}")
                
                time.sleep(1)  # Be nice to servers
                
            except Exception as e:
                print(f"❌ Error downloading photo {i+1}: {e}")

    def get_high_res_url(self, url):
        """Convert thumbnail URL to high-res version"""
        if not url:
            return url
        
        # Remove common thumbnail parameters
        clean_url = re.sub(r'[?&]w=\d+', '', url)
        clean_url = re.sub(r'[?&]h=\d+', '', clean_url)
        clean_url = re.sub(r'/w_\d+,h_\d+/', '/', clean_url)
        clean_url = re.sub(r'_thumb\.', '.', clean_url)
        
        return clean_url

    def test_single_venue(self, venue_url):
        """Test scraping one venue"""
        if not self.setup_driver():
            return None
        
        try:
            venue_data = self.scrape_single_listing(venue_url)
            
            if venue_data:
                # Save test result
                with open('single_venue_test.json', 'w') as f:
                    json.dump(venue_data, f, indent=2)
                print(f"\n💾 Saved test data to 'single_venue_test.json'")
            
            return venue_data
        finally:
            self.driver.quit()

# Test with your example URL
if __name__ == "__main__":
    scraper = PeerspaceListingScraper(headless=False)
    
    # Test with the URL you found
    test_url = "https://www.peerspace.com/pages/listings/635ca870ab68cd000ef37bf1"
    result = scraper.test_single_venue(test_url)
    
    if result:
        print("\n🎉 SUCCESS! The scraper can read individual listings!")
    else:
        print("\n❌ Still having issues - might need different approach")