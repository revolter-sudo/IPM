from typing import List, Dict

class LocationService:
    # Comprehensive dictionary of Indian states and their major cities
    _INDIA_STATES_CITIES: Dict[str, List[str]] = {
        "andhra pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Tirupati"],
        "arunachal pradesh": ["Itanagar", "Tawang", "Pasighat", "Ziro"],
        "assam": ["Guwahati", "Dibrugarh", "Silchar", "Tezpur"],
        "bihar": ["Patna", "Gaya", "Darbhanga", "Bhagalpur"],
        "chhattisgarh": ["Raipur", "Bilaspur", "Korba", "Durg", "Raigarh"],
        "goa": ["Panaji", "Vasco da Gama", "Margao", "Mapusa", "Ponda"],
        "gujarat": ["Ahmedabad", "Vadodara", "Surat", "Rajkot", "Gandhinagar", "Bhavnagar", "Jamnagar", "Junagadh"],
        "haryana": ["Faridabad", "Gurugram", "Sonipat", "Panipat", "Ambala"],
        "himachal pradesh": ["Shimla", "Dharamshala", "Mandi", "Solan", "Chamba"],
        "jharkhand": ["Ranchi", "Jamshedpur", "Bokaro", "Dhanbad", "Deoghar", "Hazaribagh"],
        "karnataka": ["Bangalore", "Mysore", "Hubli", "Mangalore", "Belgaum", "Gulbarga", "Dharwad", "Shimoga"],
        "kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam", "Palakkad"],
        "madhya pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur", "Ujjain", "Sagar"],
        "maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Aurangabad", "Solapur", "Kolhapur"],
        "manipur": ["Imphal", "Bishnupur", "Ukhrul", "Tamenglong"],
        "meghalaya": ["Shillong", "Cherrapunji", "Tura", "Jowai"],
        "mizoram": ["Aizawl", "Lunglei", "Serchhip", "Champhai"],
        "nagaland": ["Kohima", "Mokokchung", "Tuensang", "Zunheboto"],
        "odisha": ["Bhubaneswar", "Rourkela", "Cuttack", "Brahmapur", "Sambalpur", "Puri"],
        "punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
        "rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner", "Bharatpur", "Sikar"],
        "sikkim": ["Gangtok", "Namchi", "Mangan"],
        "tamil nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli", "Tiruppur", "Vellore"],
        "telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Ramagundam", "Khammam"],
        "tripura": ["Agartala", "Amarpur", "Kumarghat"],
        "uttar pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Meerut", "Allahabad", "Ghaziabad", "Noida"],
        "uttarakhand": ["Dehradun", "Haridwar", "Roorkee", "Rishikesh"],
        "west bengal": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri", "Bardhaman", "Malda"],
    }