# Sacred Iconography Showcase: Kerala Mural Style

This document presents the first set of AI-generated sacred deity artworks for the **VedaVMS / Jaimineeya** digital repository, designed in authentic **Kerala Mural temple fresco** style.

---

## 1. Generated Deity Artworks

````carousel
![Lord Shiva — Kerala Mural Painting](C:/Users/sekha/.gemini/antigravity/brain/ead1337d-82fc-4072-ba55-6124a1abd9a2/shiva_kerala_mural_1792667736680.jpg)
<!-- slide -->
![Goddess Sri Mahalakshmi — Kerala Mural Painting](C:/Users/sekha/.gemini/antigravity/brain/ead1337d-82fc-4072-ba55-6124a1abd9a2/sri_suktam_lakshmi_kerala_mural_1792667763183.jpg)
````

### Artwork Details

| Deity | Hymn Association | Iconography Highlights | Palette & Style |
| :--- | :--- | :--- | :--- |
| **Lord Shiva** *(Dhyāna Rūpam)* | **Siva Stuti / Sri Rudram / Chamakam** | Jatamakuta, Ganga, crescent moon, Tripundra vibhuti, third eye, Vasuki serpent, Trishula, Damaru, Abhaya mudra, Kamandalu | Traditional Panchavarna: cinnabar red, ochre, burnt umber, temple plaster texture |
| **Sri Mahalakshmi** *(Gajalakshmi)* | **Sri Suktam / Lakshmi Suktam** | Radiant golden complexioned Hiranyavarna, Padmasana on pink lotus, Abhaya & Varada mudras, gold coins flowing into Kalasha, twin white elephants doing abhisheka | Auspicious ochre, lotus pink, vermilion, antique gold ornaments, Kerala floral frame |

---

## 2. Optimized Repository Asset Paths

Both high-resolution originals and web-optimized WebP files have been generated and placed in the project repository:

* **Lord Shiva:**
  * Original JPEG: [`docs/assets/images/devatas/shiva_kerala_mural.jpg`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/jaimineeyasamavedam/docs/assets/images/devatas/shiva_kerala_mural.jpg)
  * Optimized WebP: [`docs/assets/images/devatas/shiva_kerala_mural.webp`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/jaimineeyasamavedam/docs/assets/images/devatas/shiva_kerala_mural.webp) *(460 KB)*
* **Sri Mahalakshmi:**
  * Original JPEG: [`docs/assets/images/devatas/sri_suktam_lakshmi_kerala_mural.jpg`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/jaimineeyasamavedam/docs/assets/images/devatas/sri_suktam_lakshmi_kerala_mural.jpg)
  * Optimized WebP: [`docs/assets/images/devatas/sri_suktam_lakshmi_kerala_mural.webp`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/jaimineeyasamavedam/docs/assets/images/devatas/sri_suktam_lakshmi_kerala_mural.webp) *(440 KB)*

---

## 3. Placement Mockups & Integration Blueprint

### Placement A: Dhyāna Card at Hymn Header (Recommended)
Placed right beneath the page header and before the first Sama mantra, pairing the sacred icon with the traditional meditation shloka:

```html
<!-- Example for Sri Suktam (docs/collection/sooktamala/kandah/supersection_20/9.html) -->
<div class="dhyana-card">
    <div class="dhyana-image-container">
        <img src="../../../../assets/images/devatas/sri_suktam_lakshmi_kerala_mural.webp" 
             alt="Sri Mahalakshmi Kerala Mural" 
             class="dhyana-image" 
             loading="lazy">
    </div>
    <div class="dhyana-text-container">
        <span class="dhyana-badge">॥ ध्यान श्लोकः ॥</span>
        <p class="dhyana-shloka">
            हिरण्यवर्णां हरिणीं सुवर्णरजतस्रजाम् ।<br>
            चन्द्रां हिरण्मयीं लक्ष्मीं जातवेदो म आवह ॥
        </p>
        <p class="dhyana-translation">
            <em>"O Agni (Jatavedas), invoke for me that Lakshmi, who is radiant like gold, endowed with yellow luster, adorned with gold and silver garlands, enchanting like the moon, and full of golden opulence."</em>
        </p>
    </div>
</div>
```

```html
<!-- Example for Siva Stuti / Sri Rudram (docs/collection/sooktamala/kandah/supersection_20/12.html) -->
<div class="dhyana-card">
    <div class="dhyana-image-container">
        <img src="../../../../assets/images/devatas/shiva_kerala_mural.webp" 
             alt="Lord Shiva Dhyana Rupam Kerala Mural" 
             class="dhyana-image" 
             loading="lazy">
    </div>
    <div class="dhyana-text-container">
        <span class="dhyana-badge">॥ ध्यान श्लोकः ॥</span>
        <p class="dhyana-shloka">
            ध्यायेन्नित्यं महेशं रजतगिरिनिभं चारुचन्द्रावतंसं<br>
            रत्नाकल्पोज्ज्वलाङ्गं परशुमृगवराभीतिहस्तं प्रसन्नम् ।
        </p>
        <p class="dhyana-translation">
            <em>"One should meditate constantly upon the Great Lord Mahesha, resplendent like a mountain of silver, adorned with the crescent moon, sparkling with gem-studded ornaments, holding the axe and deer, with hands showing the boons and protection mudras, radiating absolute serenity."</em>
        </p>
    </div>
</div>
```

### Accompanying CSS (`docs/collection/css/styles.css`)
```css
.dhyana-card {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 1.8rem;
    background: #ffffff;
    border: 1px solid #e5e0d1;
    border-left: 4px solid #852a2a;
    border-radius: 16px;
    padding: 1.25rem 1.75rem;
    margin: 1.5rem 0 2rem 0;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.dhyana-image-container {
    flex-shrink: 0;
    width: 140px;
    height: 140px;
}

.dhyana-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 12px;
    border: 1px solid #d4af37;
    box-shadow: 0 4px 10px rgba(133, 42, 42, 0.12);
}

.dhyana-text-container {
    flex-grow: 1;
}

.dhyana-badge {
    font-size: 0.8rem;
    font-weight: 700;
    color: #852a2a;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
    display: inline-block;
}

.dhyana-shloka {
    font-family: 'Noto Serif Devanagari', serif;
    font-size: 1.15rem;
    line-height: 1.7;
    color: #2c2c2c;
    margin-bottom: 0.5rem;
}

.dhyana-translation {
    font-size: 0.88rem;
    color: #666;
    line-height: 1.5;
}

@media (max-width: 650px) {
    .dhyana-card {
        flex-direction: column;
        text-align: center;
        padding: 1.2rem;
    }
    .dhyana-image-container {
        width: 120px;
        height: 120px;
    }
}
```

---

## 4. Next Batch Candidates

Following the success of this style, future deities to expand the collection include:
1. **Lord Ganesha** *(Ganapati Suktam / Section 1 opener)*
2. **Goddess Saraswati** *(Saraswati Suktam / Section 3 opener)*
3. **Cosmic Purusha / Maha Vishnu** *(Purusha Suktam / Section 6 opener)*
4. **Varuna & Agni Kalasha** *(Udakashanti Japam opener)*
