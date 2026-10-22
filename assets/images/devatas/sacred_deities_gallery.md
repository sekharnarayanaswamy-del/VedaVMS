# VedaVMS Sacred Deities Visual Web Map & Directory

A sacred, iconography-guided site directory for the VedaVMS digital Vedic repository. Each Vedic deity presides over and anchors a core section of the knowledge base.

---

## 1. Visual Web Map (Mermaid Architecture)

```mermaid
flowchart TD
    subgraph CoreGateway["Main Site Gateway"]
        direction TB
        Home["🏠 Home (index.html)<br/><b>Lord Maha Ganapati</b><br/><i>Vighnaharta & Auspicious Beginning</i>"]
        About["📜 About Us (about.html)<br/><b>Sri Adi Shankaracharya & Disciples</b><br/><i>Guru Parampara & Commentary Tradition</i>"]
        Docs["📚 Master Documents (documents.html)<br/><b>Lord Maha Vishnu</b><br/><i>Vedic Repository & Yajna Purusha</i>"]
        Conv["🔤 Vedic Conventions (convention.html)<br/><b>Goddess Gayatri Devi</b><br/><i>Veda Mata, Swaras & Metres</i>"]
    end

    subgraph CommunityGateway["Knowledge & Outreach"]
        direction TB
        Articles["✍️ Articles (articles.html)<br/><b>Lord Agni Deva</b><br/><i>Vedic Flame of Inquiry & Intellect</i>"]
        Videos["🎥 Chanting Lessons (videos.html)<br/><b>Lord Pavamana Soma</b><br/><i>Flow of Sacred Sound & Amrita</i>"]
        Donations["🪷 Support & Donations (donations.html)<br/><b>Goddess Sri Mahalakshmi</b><br/><i>Pathashala Sustenance & Abundance</i>"]
    end

    subgraph ScriptureSanctuary["Interactive HTML Scripture Viewer"]
        direction TB
        Hub["🏛️ Viewer Hub (viewer/html_viewer.html)<br/><b>Lord Shiva & Goddess Sri Mahalakshmi</b><br/><i>Auspicious Dual Presence</i>"]
        Rudram["🔱 Siva Stuti & Sri Rudram (viewer/siva_stuti_sanskrit.html)<br/><b>Lord Shiva (Dhyana Rupam)</b>"]
        Shanti["🕊️ Universal Shanti Japam (viewer/shanti_japam_sanskrit.html)<br/><b>Goddess Sri Mahalakshmi</b>"]
        SuryaPrashnam["☀️ Aruna Prashnam / Surya Namaskara (viewer/taittiriya_upanishad_sanskrit.html)<br/><b>Lord Surya / Aditya</b>"]
        Udaka["🌊 Udaka Shanti & Anushangam (viewer/udaka_shanti_sanskrit.html)<br/><b>Lord Varuna Deva</b>"]
        YajnaBrahmana["🔥 Taittiriya Brahmana 3.7 - 3.9<br/><b>Lord Agni</b> (3.7 Achidram)<br/><b>Lord Indra</b> (3.8 Vaiswadevam)<br/><b>Lord Pavamana Soma</b> (3.9 Havirdhanam)"]
    end

    Home --> About
    Home --> Docs
    Home --> Conv
    Home --> Articles
    Home --> Videos
    Home --> Donations
    Docs --> Hub
    Hub --> Rudram
    Hub --> Shanti
    Hub --> SuryaPrashnam
    Hub --> Udaka
    Hub --> YajnaBrahmana
```

---

## 2. Sacred Art Carousel

All 11 sacred deity paintings adhere to the classical temple fresco style with warm mineral pigments and fine calligraphic outlines:

````carousel
![Lord Maha Ganapati](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/lord_ganapati_1792696264420.jpg)
<!-- slide -->
![Sri Adi Shankaracharya and Disciples](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/shankara_and_disciples_1792694408455.jpg)
<!-- slide -->
![Lord Maha Vishnu](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/lord_vishnu_1792694472246.jpg)
<!-- slide -->
![Goddess Gayatri Devi (Veda Mata)](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/goddess_gayatri_devi_1792697275152.jpg)
<!-- slide -->
![Lord Surya / Aditya](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/kerala_mural_surya_narayana_1792698097883.jpg)
<!-- slide -->
![Lord Shiva](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/shiva_kerala_mural.jpg)
<!-- slide -->
![Goddess Sri Mahalakshmi](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/sri_suktam_lakshmi_kerala_mural.jpg)
<!-- slide -->
![Lord Agni Deva](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/agni_deva_1792694417861.jpg)
<!-- slide -->
![Lord Indra Deva](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/indra_deva_1792694445347.jpg)
<!-- slide -->
![Lord Varuna Deva](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/varuna_deva_1792694467176.jpg)
<!-- slide -->
![Lord Pavamana Soma](C:/Users/sekha/.gemini/antigravity/brain/51244ec3-ec32-41e8-8dd0-c670bb47f814/pavamana_soma_1792694803205.jpg)
````

---

## 3. Web Map Directory & Page Navigation

### Gateway I: Main Site Core
| Deity Presiding | Local Page Link | Vedic Significance |
| :--- | :--- | :--- |
| **Lord Maha Ganapati** | [mockup/index.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/index.html) | Auspicious portal invocation (*Om Shri Mahaganapathaye Namaha*), remover of obstacles. |
| **Sri Adi Shankaracharya & Disciples** | [mockup/about.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/about.html) | Guru Parampara lineage, upholding authentic Advaita Vedic tradition. |
| **Lord Maha Vishnu** | [mockup/documents.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/documents.html) | *Yajño vai Viṣṇuḥ* — cosmic preserver guarding the 972+ master Vedic texts and PDFs. |
| **Goddess Gayatri Devi** | [mockup/convention.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/convention.html) | *Veda Mātā* — Mother of Vedic wisdom, presiding over swaras, accents, and pronunciation. |

### Gateway II: Knowledge & Community
| Deity Presiding | Local Page Link | Vedic Significance |
| :--- | :--- | :--- |
| **Lord Agni Deva** | [mockup/articles.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/articles.html) | *Purohitam Yajnasa* — the celestial flame illuminating research, articles, and commentaries. |
| **Lord Pavamana Soma** | [mockup/videos.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/videos.html) | Flowing amrita of sacred sound, presiding over multimedia and oral chanting lessons. |
| **Goddess Sri Mahalakshmi** | [mockup/donations.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/donations.html) | Divine auspiciousness and sustenance supporting traditional Veda Pathashalas. |

### Gateway III: Interactive Scripture Sanctuary (HTML Viewer)
| Deity Presiding | Local Page Link | Vedic Hymn / Context |
| :--- | :--- | :--- |
| **Lord Shiva & Goddess Mahalakshmi** | [mockup/viewer/html_viewer.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/html_viewer.html) | Dual Hero welcoming seekers to the interactive reader. |
| **Lord Shiva** *(Dhyāna Rūpam)* | [mockup/viewer/siva_stuti_sanskrit.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/siva_stuti_sanskrit.html) | Siva Stuti, Sri Rudram (Namakam), and Chamakam. |
| **Goddess Sri Mahalakshmi** | [mockup/viewer/shanti_japam_sanskrit.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/shanti_japam_sanskrit.html) | Universal Shanti Mantras and peace prayers. |
| **Lord Surya / Aditya** | [mockup/viewer/taittiriya_upanishad_sanskrit.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/taittiriya_upanishad_sanskrit.html) | Taittiriya Aranyakam Prashna 1 (**Aruna Prashnam / Surya Namaskara Mantras**). |
| **Lord Varuna Deva** | [mockup/viewer/udaka_shanti_sanskrit.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/udaka_shanti_sanskrit.html) | Udaka Shanti ritual water sanctification hymns. |
| **Lord Varuna Deva** | [mockup/viewer/udaka_shanti_anushangam_sanskrit.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/udaka_shanti_anushangam_sanskrit.html) | Udaka Shanti Anushangam supplementary chants. |
| **Lord Agni Deva** | [mockup/viewer/tb_3_7_achidram_sanskrit.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/tb_3_7_achidram_sanskrit.html) | Taittiriya Brahmana 3.7 Achidram (Sacrificial integrity). |
| **Lord Indra Deva** | [mockup/viewer/tb_3_8_aswamedham_vaiswadevam_sanskrit.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/tb_3_8_aswamedham_vaiswadevam_sanskrit.html) | TB 3.8 Aswamedham Vaiswadevam (Cosmic sovereignty). |
| **Lord Pavamana Soma** | [mockup/viewer/tb_3_9_aswamedham_havirdhanam_sanskrit.html](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/viewer/tb_3_9_aswamedham_havirdhanam_sanskrit.html) | TB 3.9 Aswamedham Havirdhanam (Celestial oblations). |

---

## 4. Physical Asset Integrity

All illustrations are located at:
- Master repository: [`assets/images/devatas/`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/assets/images/devatas/)
- Mockup preview: [`mockup/assets/images/devatas/`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/mockup/assets/images/devatas/)
- Production build: [`build/assets/images/devatas/`](file:///c:/Users/sekha/OneDrive/Documents/GitHub/vedavms/build/assets/images/devatas/)
