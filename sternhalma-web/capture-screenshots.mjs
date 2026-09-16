import puppeteer from 'puppeteer';
import fs from 'fs';

const screenshotDir = './screenshots';
if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir);
}

(async () => {
    console.log("Launching browser...");
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    
    // Modern dark theme means we should enable dark mode in browser if it respects system
    await page.emulateMediaFeatures([
        { name: 'prefers-color-scheme', value: 'dark' }
    ]);
    
    await page.setViewport({ width: 1280, height: 800 });
    
    console.log("Navigating to welcome screen...");
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle0' });
    
    console.log("Taking screenshot of welcome screen...");
    await page.screenshot({ path: `${screenshotDir}/welcome.png` });
    
    console.log("Navigating to game screen...");
    // click join game to see the board
    await page.click('button[type="submit"]');
    
    // Give time string "Status: Connecting" to fade or appear, 
    // and wait for svg board to show up
    await page.waitForSelector('svg', { timeout: 10000 });
    await new Promise(r => setTimeout(r, 1000)); 
    
    console.log("Taking screenshot of game screen...");
    await page.screenshot({ path: `${screenshotDir}/game.png` });

    await browser.close();
    console.log("Done.");
})();
