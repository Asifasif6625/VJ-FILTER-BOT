# Multilingual Help, About, and DMCA UI for Child Bot
import html
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils import get_delivery_bot_username, temp
from info import CHNL_LNK, CLONE_MODE, PICS

LANGUAGES = [
    ("🇬🇧 English", "eng"),
    ("🇮🇳 മലയാളം", "mal"),
    ("🇮🇳 தமிழ்", "tam"),
    ("🇮🇳 हिन्दी", "hin"),
    ("🇮🇳 తెలుగు", "tel"),
    ("🇮🇳 ಕನ್ನಡ", "kan"),
]

HELP_TEXTS = {
    "eng": (
        "<b>✨ <u>Help Menu</u></b>\n\n"
        "Here is how you can use this bot:\n"
        "• Type the name of any Movie or Series in the chat.\n"
        "• You will get interactive buttons for Language, Season & Quality.\n"
        "• Click on your preferred Quality to receive files instantly.\n"
        "• Files are sent directly in PM.\n\n"
        "<i>⚠️ Note: Files are automatically deleted in 1 minute due to copyright issues. Make sure to forward them to Saved Messages immediately!</i>"
    ),
    "mal": (
        "<b>✨ <u>സഹായം (Help)</u></b>\n\n"
        "ഈ ബോട്ട് എങ്ങനെ ഉപയോഗിക്കാം:\n"
        "• നിങ്ങൾക്കാവശ്യമുള്ള സിനിമയുടെയോ സീരീസിന്റെയോ പേര് ചാറ്റിൽ അയക്കുക.\n"
        "• ലഭ്യമായ ഭാഷ, സീസൺ, ക്വാളിറ്റി ബട്ടണുകൾ ലഭിക്കും.\n"
        "• ആവശ്യമായ ക്വാളിറ്റി ക്ലിക്ക് ചെയ്താൽ ഫയലുകൾ ഉടൻ ലഭിക്കും.\n\n"
        "<i>⚠️ ശ്രദ്ധിക്കുക: കോപ്പിറൈറ്റ് ഉള്ളതിനാൽ ലഭിക്കുന്ന ഫയലുകൾ 1 മിനിറ്റിനുള്ളിൽ ഡിലീറ്റ് ആകും. അതിനാൽ ഉടൻ തന്നെ 'Saved Messages' ലേക്ക് ഫോർവേഡ് ചെയ്യുക!</i>"
    ),
    "tam": (
        "<b>✨ <u>உதவி (Help)</u></b>\n\n"
        "இந்த போட்டை எவ்வாறு பயன்படுத்துவது:\n"
        "• படம் அல்லது தொடரின் பெயரை சாட்டில் அனுப்பவும்.\n"
        "• மொழி, சீசன் மற்றும் தரம் கொண்ட பட்டன்கள் தோன்றும்.\n"
        "• உங்கள் விருப்பமான தரத்தை கிளிக் செய்து கோப்புகளை உடனே பெறுங்கள்.\n\n"
        "<i>⚠️ குறிப்பு: பதிப்புரிமை காரணமாக கோப்புகள் 1 நிமிடத்தில் நீக்கப்படும். உடனடியாக Saved Messages-க்கு அனுப்பவும்!</i>"
    ),
    "hin": (
        "<b>✨ <u>सहायता (Help)</u></b>\n\n"
        "इस बॉट का उपयोग कैसे करें:\n"
        "• चैट में किसी भी मूवी या वेब सीरीज़ का नाम लिखें।\n"
        "• आपको भाषा, सीज़न और क्वालिटी के बटन मिलेंगे।\n"
        "• अपनी पसंदीदा क्वालिटी पर क्लिक करें और फाइलें पाएं।\n\n"
        "<i>⚠️ ध्यान दें: कॉपीराइट के कारण फाइलें 1 मिनट में डिलीट हो जाएंगी। तुरंत Saved Messages में फॉरवर्ड करें!</i>"
    ),
    "tel": (
        "<b>✨ <u>సహాయం (Help)</u></b>\n\n"
        "ఈ బాట్‌ను ఎలా ఉపయోగించాలి:\n"
        "• ఏదైనా సినిమా లేదా సిరీస్ పేరును చాట్‌లో టైప్ చేయండి.\n"
        "• భాష, సీజన్ మరియు క్వాలిటీ బటన్లు కనిపిస్తాయి.\n"
        "• మీ ప్రాధాన్యత క్వాలిటీని ఎంచుకుని ఫైల్‌లను వెంటనే పొందండి.\n\n"
        "<i>⚠️ గమనిక: కాపీరైట్ సమస్యల వల్ల ఫైల్స్ 1 నిమిషంలో డిలీట్ చేయబడతాయి. వెంటనే Saved Messages కి ఫార్వర్డ్ చేయండి!</i>"
    ),
    "kan": (
        "<b>✨ <u>ಸಹಾಯ (Help)</u></b>\n\n"
        "ಈ ಬಾಟ್ ಅನ್ನು ಹೇಗೆ ಬಳಸುವುದು:\n"
        "• ಯಾವುದೇ ಚಲನಚಿತ್ರ ಅಥವಾ ಸರಣಿಯ ಹೆಸರನ್ನು ಚಾಟ್‌ನಲ್ಲಿ ಟೈಪ್ ಮಾಡಿ.\n"
        "• ಭಾಷೆ, ಸೀಸನ್ ಮತ್ತು ಗುಣಮಟ್ಟದ ಬಟನ್‌ಗಳು ಕಾಣಿಸಿಕೊಳ್ಳುತ್ತವೆ.\n"
        "• ಗುಣಮಟ್ಟವನ್ನು ಆಯ್ಕೆಮಾಡಿ ಫೈಲ್‌ಗಳನ್ನು ತಕ್ಷಣ ಪಡೆಯಿರಿ.\n\n"
        "<i>⚠️ ಗಮನಿಸಿ: ಕೃತಿಸ್ವಾಮ್ಯದ ಕಾರಣ 1 ನಿಮಿಷದಲ್ಲಿ ಫೈಲ್‌ಗಳು ಅಳಿಸಲ್ಪಡುತ್ತವೆ. ತಕ್ಷಣವೇ Saved Messages ಗೆ ಫಾರ್ವರ್ಡ್ ಮಾಡಿ!</i>"
    )
}

ABOUT_TEXTS = {
    "eng": (
        "<b>🔰 <u>About Bot</u></b>\n\n"
        "• <b>Bot Name:</b> {bot_name}\n"
        "• <b>Developer:</b> Oreo\n"
        "• <b>Framework:</b> Pyrogram (Python 3)\n"
        "• <b>Database:</b> MongoDB\n"
        "• <b>Status:</b> Active & Super Fast ⚡\n\n"
        "<i>A high-speed Telegram media search and delivery bot.</i>"
    ),
    "mal": (
        "<b>🔰 <u>ബോട്ടിനെക്കുറിച്ച് (About)</u></b>\n\n"
        "• <b>ബോട്ടിന്റെ പേര്:</b> {bot_name}\n"
        "• <b>ഡെവലപ്പർ:</b> Oreo\n"
        "• <b>ഫ്രെയിംവർക്ക്:</b> Pyrogram (Python 3)\n"
        "• <b>ഡാറ്റാബേസ്:</b> MongoDB\n"
        "• <b>സ്റ്റാറ്റസ്:</b> Active & Super Fast ⚡"
    ),
    "tam": (
        "<b>🔰 <u>போட் பற்றி (About)</u></b>\n\n"
        "• <b>போட் பெயர்:</b> {bot_name}\n"
        "• <b>டெவலப்பர்:</b> Oreo\n"
        "• <b>தொழில்நுட்பம்:</b> Pyrogram (Python 3)\n"
        "• <b>தரவுத்தளம்:</b> MongoDB\n"
        "• <b>நிலை:</b> Active & Super Fast ⚡"
    ),
    "hin": (
        "<b>🔰 <u>बॉट के बारे में (About)</u></b>\n\n"
        "• <b>बॉट का नाम:</b> {bot_name}\n"
        "• <b>डेवलपर:</b> Oreo\n"
        "• <b>फ्रेमवर्क:</b> Pyrogram (Python 3)\n"
        "• <b>डेटाबेस:</b> MongoDB\n"
        "• <b>स्थिति:</b> Active & Super Fast ⚡"
    ),
    "tel": (
        "<b>🔰 <u>బాట్ గురించి (About)</u></b>\n\n"
        "• <b>బాట్ పేరు:</b> {bot_name}\n"
        "• <b>డెవలపర్:</b> Oreo\n"
        "• <b>టెక్నాలజీ:</b> Pyrogram (Python 3)\n"
        "• <b>డేటాబేస్:</b> MongoDB\n"
        "• <b>స్థితి:</b> Active & Super Fast ⚡"
    ),
    "kan": (
        "<b>🔰 <u>ಬಾಟ್ ಬಗ್ಗೆ (About)</u></b>\n\n"
        "• <b>ಬಾಟ್ ಹೆಸರು:</b> {bot_name}\n"
        "• <b>ಡೆವಲಪರ್:</b> Oreo\n"
        "• <b>ತಂತ್ರಜ್ಞಾನ:</b> Pyrogram (Python 3)\n"
        "• <b>ಡೇಟಾಬೇಸ್:</b> MongoDB\n"
        "• <b>ಸ್ಥಿತಿ:</b> Active & Super Fast ⚡"
    )
}

DMCA_TEXTS = {
    "eng": (
        "<b>⚖️ <u>DMCA & Copyright Disclaimer</u></b>\n\n"
        "<blockquote><b>We do not host or store any files on our servers.</b></blockquote>\n\n"
        "• This bot only indexes and searches media links that are already publicly shared on Telegram channels and third-party groups.\n"
        "• No copyrighted content is stored or hosted directly on our servers or databases.\n"
        "• All rights belong to their respective copyright owners.\n"
        "• If you have any copyright concerns or wish to request removal of indexed links, please contact the originating Telegram channel admins or Telegram DMCA support (dmca@telegram.org)."
    ),
    "mal": (
        "<b>⚖️ <u>DMCA & പകർപ്പവകാശ നിരാകരണം</u></b>\n\n"
        "<blockquote><b>ഞങ്ങൾ ഞങ്ങളുടെ സെർവറുകളിൽ ഒരു ഫയലും ഹോസ്റ്റ് ചെയ്യുകയോ സൂക്ഷിക്കുകയോ ചെയ്യുന്നില്ല.</b></blockquote>\n\n"
        "• ടെലിഗ്രാമിൽ ലഭ്യമായ പബ്ലിക് ചാനലുകളിലെ ലിങ്കുകൾ കണ്ടെത്താൻ മാത്രമേ ഈ ബോട്ട് സഹായിക്കുന്നുള്ളൂ.\n"
        "• യാതൊരു വിധത്തിലുള്ള മീഡിയ ഫയലുകളും ഈ ബോട്ടിലോ ഞങ്ങളുടെ സെർവറിലോ അപ്‌ലോഡ് ചെയ്തിട്ടില്ല.\n"
        "• എല്ലാ അവകാശങ്ങളും അതത് ഉടമസ്ഥർക്ക് മാത്രമുള്ളതാണ്.\n"
        "• പരാതികൾക്ക് ബന്ധപ്പെട്ട ടെലിഗ്രാം ചാനൽ അഡ്മിനുമായോ ടെലിഗ്രാം സപ്പോർട്ടുമായോ (dmca@telegram.org) ബന്ധപ്പെടുക."
    ),
    "tam": (
        "<b>⚖️ <u>DMCA & பதிப்புரிமை மறுப்பு</u></b>\n\n"
        "<blockquote><b>நாங்கள் எந்த கோப்புகளையும் எங்கள் சேவையகங்களில் சேமிப்பதோ அல்லது ஹோஸ்ட் செய்வதோ இல்லை.</b></blockquote>\n\n"
        "• டெலிகிராமில் ஏற்கனவே உள்ள பொது இணைப்புகளைத் தேட மட்டுமே இந்த போட் பயன்படுகிறது.\n"
        "• பதிப்புரிமை பெற்ற எந்த உள்ளடக்கமும் எங்கள் தளத்தில் பதிவேற்றப்படவில்லை.\n"
        "• பதிப்புரிமை புகார்களுக்கு சம்பந்தப்பட்ட டெலிகிராம் சேனல் நிர்வாகிகளைத் தொடர்பு கொள்ளவும்."
    ),
    "hin": (
        "<b>⚖️ <u>DMCA और कॉपीराइट अस्वीकरण</u></b>\n\n"
        "<blockquote><b>हम अपने सर्वर पर कोई भी फ़ाइल होस्ट या स्टोर नहीं करते हैं।</b></blockquote>\n\n"
        "• यह बॉट केवल टेलीग्राम पर पहले से सार्वजनिक रूप से मौजूद लिंक्स को खोजने में मदद करता है।\n"
        "• किसी भी कॉपीराइट सामग्री को हमारे सर्वर पर अपलोड नहीं किया गया है।\n"
        "• सभी अधिकार उनके संबंधित स्वामियों के हैं।\n"
        "• किसी भी शिकायत के लिए मूल टेलीग्राम चैनल या dmca@telegram.org पर संपर्क करें।"
    ),
    "tel": (
        "<b>⚖️ <u>DMCA & కాపీరైట్ డిస్క్లైమర్</u></b>\n\n"
        "<blockquote><b>మేము మా సర్వర్లలో ఎటువంటి ఫైల్‌లను హోస్ట్ చేయడం లేదా నిల్వ చేయడం లేదు.</b></blockquote>\n\n"
        "• టెలిగ్రామ్‌లో పబ్లిక్‌గా ఉన్న లింకులను మాత్రమే ఈ బాట్ శోధిస్తుంది.\n"
        "• మా డేటాబేస్‌లో ఎటువంటి మీడియా ఫైల్స్ అప్‌లోడ్ చేయబడలేదు.\n"
        "• సమస్యల కోసం సంబంధిత టెలిగ్రామ్ ఛానెల్ అడ్మిన్లను సంప్రదించండి."
    ),
    "kan": (
        "<b>⚖️ <u>DMCA & ಹಕ್ಕುಸ್ವಾಮ್ಯ ಹಕ್ಕುತ್ಯಾಗ</u></b>\n\n"
        "<blockquote><b>ನಾವು ಯಾವುದೇ ಫೈಲ್‌ಗಳನ್ನು ನಮ್ಮ ಸರ್ವರ್‌ಗಳಲ್ಲಿ ಹೋಸ್ಟ್ ಮಾಡುವುದಿಲ್ಲ.</b></blockquote>\n\n"
        "• ಟೆಲಿಗ್ರಾಮ್‌ನಲ್ಲಿ ಸಾರ್ವಜನಿಕವಾಗಿ ಲಭ್ಯವಿರುವ ಲಿಂಕ್‌ಗಳನ್ನು ಮಾತ್ರ ಈ ಬಾಟ್ ಹುಡುಕುತ್ತದೆ.\n"
        "• ಯಾವುದೇ ಮಾಧ್ಯಮ ಫೈಲ್‌ಗಳು ನಮ್ಮ ಸರ್ವರ್‌ನಲ್ಲಿ ಸಂಗ್ರಹವಾಗಿಲ್ಲ.\n"
        "• ಹಕ್ಕುಸ್ವಾಮ್ಯ ಉಲ್ಲಂಘನೆಗಾಗಿ ಮೂಲ ಟೆಲಿಗ್ರಾಮ್ ಚಾನೆಲ್ ಅಡ್ಮಿನ್‌ಗಳನ್ನು ಸಂಪರ್ಕಿಸಿ."
    )
}

def build_lang_keyboard(section: str, current_lang: str = "eng") -> InlineKeyboardMarkup:
    """Builds interactive language switcher buttons with Home back button."""
    buttons = []
    row1 = []
    for label, code in LANGUAGES[:3]:
        disp = f"• {label} •" if code == current_lang else label
        row1.append(InlineKeyboardButton(disp, callback_data=f"user_{section}#{code}"))
    buttons.append(row1)

    row2 = []
    for label, code in LANGUAGES[3:]:
        disp = f"• {label} •" if code == current_lang else label
        row2.append(InlineKeyboardButton(disp, callback_data=f"user_{section}#{code}"))
    buttons.append(row2)

    buttons.append([InlineKeyboardButton("🏠 Home", callback_data="user_home")])
    return InlineKeyboardMarkup(buttons)

def build_start_menu_keyboard() -> InlineKeyboardMarkup:
    """Builds the main start menu for Child Bot."""
    buttons = []
    if CHNL_LNK:
        buttons.append([InlineKeyboardButton("📢 Updates Channel", url=CHNL_LNK)])
    buttons.append([
        InlineKeyboardButton("ℹ️ Help", callback_data="user_help#eng"),
        InlineKeyboardButton("🔰 About", callback_data="user_about#eng")
    ])
    buttons.append([
        InlineKeyboardButton("⚖️ DMCA Disclaimer", callback_data="user_dmca#eng")
    ])
    if CLONE_MODE:
        buttons.append([InlineKeyboardButton("🤖 Create Clone Bot", callback_data="clone")])
    return InlineKeyboardMarkup(buttons)

def get_help_card(lang: str = "eng") -> tuple[str, InlineKeyboardMarkup]:
    text = HELP_TEXTS.get(lang, HELP_TEXTS["eng"])
    return text, build_lang_keyboard("help", lang)

def get_about_card(bot_name: str, lang: str = "eng") -> tuple[str, InlineKeyboardMarkup]:
    tmpl = ABOUT_TEXTS.get(lang, ABOUT_TEXTS["eng"])
    text = tmpl.format(bot_name=bot_name or "Filter Bot")
    return text, build_lang_keyboard("about", lang)

def get_dmca_card(lang: str = "eng") -> tuple[str, InlineKeyboardMarkup]:
    text = DMCA_TEXTS.get(lang, DMCA_TEXTS["eng"])
    return text, build_lang_keyboard("dmca", lang)

