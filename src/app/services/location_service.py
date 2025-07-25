from typing import Dict

class LocationService:
    # Comprehensive dictionary of Indian states and their major cities
    # _INDIA_STATES_CITIES: Dict[str, List[str]] = {
    #     "andhra pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Tirupati"],
    #     "arunachal pradesh": ["Itanagar", "Tawang", "Pasighat", "Ziro"],
    #     "assam": ["Guwahati", "Dibrugarh", "Silchar", "Tezpur"],
    #     "bihar": ["Patna", "Gaya", "Darbhanga", "Bhagalpur"],
    #     "chhattisgarh": ["Raipur", "Bilaspur", "Korba", "Durg", "Raigarh"],
    #     "goa": ["Panaji", "Vasco da Gama", "Margao", "Mapusa", "Ponda"],
    #     "gujarat": ["Ahmedabad", "Vadodara", "Surat", "Rajkot", "Gandhinagar", "Bhavnagar", "Jamnagar", "Junagadh"],
    #     "haryana": ["Faridabad", "Gurugram", "Sonipat", "Panipat", "Ambala"],
    #     "himachal pradesh": ["Shimla", "Dharamshala", "Mandi", "Solan", "Chamba"],
    #     "jharkhand": ["Ranchi", "Jamshedpur", "Bokaro", "Dhanbad", "Deoghar", "Hazaribagh"],
    #     "karnataka": ["Bangalore", "Mysore", "Hubli", "Mangalore", "Belgaum", "Gulbarga", "Dharwad", "Shimoga"],
    #     "kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam", "Palakkad"],
    #     "madhya pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur", "Ujjain", "Sagar"],
    #     "maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Aurangabad", "Solapur", "Kolhapur"],
    #     "manipur": ["Imphal", "Bishnupur", "Ukhrul", "Tamenglong"],
    #     "meghalaya": ["Shillong", "Cherrapunji", "Tura", "Jowai"],
    #     "mizoram": ["Aizawl", "Lunglei", "Serchhip", "Champhai"],
    #     "nagaland": ["Kohima", "Mokokchung", "Tuensang", "Zunheboto"],
    #     "odisha": ["Bhubaneswar", "Rourkela", "Cuttack", "Brahmapur", "Sambalpur", "Puri"],
    #     "punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
    #     "rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner", "Bharatpur", "Sikar"],
    #     "sikkim": ["Gangtok", "Namchi", "Mangan"],
    #     "tamil nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli", "Tiruppur", "Vellore"],
    #     "telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Ramagundam", "Khammam"],
    #     "tripura": ["Agartala", "Amarpur", "Kumarghat"],
    #     "uttar pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Meerut", "Allahabad", "Ghaziabad", "Noida"],
    #     "uttarakhand": ["Dehradun", "Haridwar", "Roorkee", "Rishikesh"],
    #     "west bengal": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri", "Bardhaman", "Malda"],
    # }

    _INDIA_STATES_CITIES = {
        # States
        "andhra pradesh": [
            "Amaravati",
            "Visakhapatnam",
            "Vijayawada",
            "Guntur",
            "Tirupati",
            "Vijayawada",
        ],
        "arunachal pradesh": ["Itanagar", "Tawang", "Pasighat", "Ziro"],
        "assam": ["Dispur", "Guwahati", "Dibrugarh", "Silchar", "Tezpur"],
        "bihar": ["Patna", "Gaya", "Darbhanga", "Bhagalpur"],
        "chhattisgarh": ["Raipur", "Bilaspur", "Korba", "Durg", "Raigarh"],
        "goa": ["Panaji", "Margao", "Vasco da Gama", "Mapusa", "Ponda"],
        "gujarat": [
            "Gandhinagar",
            "Ahmedabad",
            "Vadodara",
            "Surat",
            "Rajkot",
            "Bhavnagar",
            "Jamnagar",
            "Junagadh",
        ],
        "haryana": [
            "Chandigarh",
            "Faridabad",
            "Gurugram",
            "Sonipat",
            "Panipat",
            "Ambala",
        ],
        "himachal pradesh": ["Shimla", "Dharamshala", "Mandi", "Solan", "Chamba"],
        "jharkhand": [
            "Ranchi",
            "Jamshedpur",
            "Bokaro",
            "Dhanbad",
            "Deoghar",
            "Hazaribagh",
        ],
        "karnataka": [
            "Bengaluru",
            "Mysore",
            "Hubli",
            "Mangalore",
            "Belgaum",
            "Gulbarga",
            "Dharwad",
            "Shimoga",
        ],
        "kerala": [
            "Thiruvananthapuram",
            "Kochi",
            "Kozhikode",
            "Thrissur",
            "Kollam",
            "Palakkad",
        ],
        "madhya pradesh": [
            "Bhopal",
            "Indore",
            "Gwalior",
            "Jabalpur",
            "Ujjain",
            "Sagar",
        ],
        "maharashtra": [
            "Mumbai",
            "Pune",
            "Nagpur",
            "Thane",
            "Nashik",
            "Aurangabad",
            "Solapur",
            "Kolhapur",
        ],
        "manipur": ["Imphal", "Bishnupur", "Ukhrul", "Tamenglong"],
        "meghalaya": ["Shillong", "Cherrapunji", "Tura", "Jowai"],
        "mizoram": ["Aizawl", "Lunglei", "Serchhip", "Champhai"],
        "nagaland": ["Kohima", "Mokokchung", "Tuensang", "Zunheboto"],
        "odisha": [
            "Bhubaneswar",
            "Cuttack",
            "Rourkela",
            "Brahmapur",
            "Sambalpur",
            "Puri",
        ],
        "punjab": ["Chandigarh", "Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
        "rajasthan": [
            "Jaipur",
            "Jodhpur",
            "Udaipur",
            "Kota",
            "Ajmer",
            "Bikaner",
            "Bharatpur",
            "Sikar",
        ],
        "sikkim": ["Gangtok", "Namchi", "Mangan"],
        "tamil nadu": [
            "Chennai",
            "Coimbatore",
            "Madurai",
            "Salem",
            "Tiruchirappalli",
            "Tiruppur",
            "Vellore",
        ],
        "telangana": [
            "Hyderabad",
            "Warangal",
            "Nizamabad",
            "Karimnagar",
            "Ramagundam",
            "Khammam",
        ],
        "tripura": ["Agartala", "Amarpur", "Kumarghat"],
        "uttar pradesh": [
            "Lucknow",
            "Kanpur",
            "Varanasi",
            "Agra",
            "Meerut",
            "Allahabad",
            "Ghaziabad",
            "Noida",
        ],
        "uttarakhand": ["Dehradun", "Nainital", "Haridwar", "Roorkee", "Rishikesh"],
        "west bengal": [
            "Kolkata",
            "Howrah",
            "Durgapur",
            "Asansol",
            "Siliguri",
            "Bardhaman",
            "Malda",
        ],
        # Union Territories
        "andaman and nicobar islands": ["Port Blair"],
        "chandigarh": ["Chandigarh"],
        "dadra and nagar haveli and daman and diu": ["Daman", "Silvassa"],
        "delhi": ["New Delhi", "Delhi"],
        "jammu and kashmir": ["Srinagar", "Jammu"],
        "ladakh": ["Leh", "Kargil"],
        "lakshadweep": ["Kavaratti"],
        "puducherry": ["Puducherry", "Pondicherry"],
        # Major NCR satellite cities
        "_ncr": [
            "Noida",
            "Greater Noida",
            "Gurugram",
            "Faridabad",
            "Ghaziabad",
            "Meerut",
            "Alwar",
            "Baghpat",
            "Panipat",
            "Karnal",
        ],
    }

    @classmethod
    def validate_coordinates(cls, latitude: float, longitude: float) -> bool:
        """
        Validate latitude and longitude coordinates.

        Args:
            latitude: Latitude value to validate
            longitude: Longitude value to validate

        Returns:
            bool: True if coordinates are valid, False otherwise
        """
        try:
            # Check if latitude is within valid range (-90 to 90)
            if not -90 <= latitude <= 90:
                return False

            # Check if longitude is within valid range (-180 to 180)
            if not -180 <= longitude <= 180:
                return False

            return True
        except (TypeError, ValueError):
            return False

    @classmethod
    def get_coordinate_precision(cls, latitude: float, longitude: float) -> str:
        """
        Determine the precision level of coordinates.

        Args:
            latitude: Latitude value
            longitude: Longitude value

        Returns:
            str: Precision level (high, medium, low)
        """
        try:
            # Count decimal places
            lat_decimals = len(str(latitude).split('.')[-1]) if '.' in str(latitude) else 0
            lon_decimals = len(str(longitude).split('.')[-1]) if '.' in str(longitude) else 0

            min_decimals = min(lat_decimals, lon_decimals)

            if min_decimals >= 6:
                return "high"  # ~1 meter precision
            elif min_decimals >= 4:
                return "medium"  # ~10 meter precision
            else:
                return "low"  # >100 meter precision
        except:
            return "unknown"

    @classmethod
    def calculate_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the distance between two coordinates using Haversine formula.

        Args:
            lat1, lon1: First coordinate pair
            lat2, lon2: Second coordinate pair

        Returns:
            float: Distance in kilometers
        """
        try:
            import math

            # Convert latitude and longitude from degrees to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))

            # Radius of earth in kilometers
            r = 6371

            return c * r
        except:
            return 0.0

    @classmethod
    def is_within_radius(cls, center_lat: float, center_lon: float,
                        point_lat: float, point_lon: float, radius_km: float) -> bool:
        """
        Check if a point is within a specified radius of a center point.

        Args:
            center_lat, center_lon: Center point coordinates
            point_lat, point_lon: Point to check coordinates
            radius_km: Radius in kilometers

        Returns:
            bool: True if point is within radius, False otherwise
        """
        try:
            distance = cls.calculate_distance(center_lat, center_lon, point_lat, point_lon)
            return distance <= radius_km
        except:
            return False

    @classmethod
    def validate_location_for_attendance(cls, latitude: float, longitude: float,
                                       project_location: dict = None) -> dict:
        """
        Validate location coordinates for attendance marking.

        Args:
            latitude: Latitude to validate
            longitude: Longitude to validate
            project_location: Optional project location for proximity check

        Returns:
            dict: Validation result with status and details
        """
        result = {
            "is_valid": False,
            "precision": "unknown",
            "warnings": [],
            "errors": []
        }

        try:
            # Basic coordinate validation
            if not cls.validate_coordinates(latitude, longitude):
                result["errors"].append("Invalid coordinates provided")
                return result

            # Check coordinate precision
            precision = cls.get_coordinate_precision(latitude, longitude)
            result["precision"] = precision

            if precision == "low":
                result["warnings"].append("Low coordinate precision detected")

            # Check if coordinates are in India (rough bounds)
            india_bounds = {
                "min_lat": 6.0,
                "max_lat": 37.0,
                "min_lon": 68.0,
                "max_lon": 97.0
            }

            if not (india_bounds["min_lat"] <= latitude <= india_bounds["max_lat"] and
                    india_bounds["min_lon"] <= longitude <= india_bounds["max_lon"]):
                result["warnings"].append("Coordinates appear to be outside India")

            # Check proximity to project location if provided
            if project_location:
                try:
                    project_lat = project_location.get("latitude")
                    project_lon = project_location.get("longitude")
                    max_distance = project_location.get("max_distance_km", 5.0)  # Default 5km radius

                    if project_lat and project_lon:
                        if not cls.is_within_radius(project_lat, project_lon,
                                                  latitude, longitude, max_distance):
                            result["warnings"].append(f"Location is more than {max_distance}km from project site")
                except:
                    result["warnings"].append("Could not validate proximity to project location")

            result["is_valid"] = True
            return result

        except Exception as e:
            result["errors"].append(f"Location validation error: {str(e)}")
            return result

    @classmethod
    def get_location_info(cls, latitude: float, longitude: float) -> dict:
        """
        Get location information including state/city if possible.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            dict: Location information
        """
        result = {
            "latitude": latitude,
            "longitude": longitude,
            "precision": cls.get_coordinate_precision(latitude, longitude),
            "is_valid": cls.validate_coordinates(latitude, longitude),
            "estimated_state": None,
            "estimated_city": None
        }

        if not result["is_valid"]:
            return result

        # Simple state estimation based on coordinate ranges
        # This is a basic implementation - in production, you might use a geocoding service
        try:
            for state, cities in cls._INDIA_STATES_CITIES.items():
                # Very rough state boundary estimation
                if state == "delhi" and 28.4 <= latitude <= 28.9 and 76.8 <= longitude <= 77.3:
                    result["estimated_state"] = "Delhi"
                    result["estimated_city"] = "New Delhi"
                    break
                elif state == "maharashtra" and 18.0 <= latitude <= 21.0 and 72.0 <= longitude <= 80.0:
                    result["estimated_state"] = "Maharashtra"
                    if 18.8 <= latitude <= 19.3 and 72.7 <= longitude <= 73.0:
                        result["estimated_city"] = "Mumbai"
                    elif 18.4 <= latitude <= 18.7 and 73.7 <= longitude <= 74.0:
                        result["estimated_city"] = "Pune"
                    break
                elif state == "karnataka" and 12.0 <= latitude <= 18.0 and 74.0 <= longitude <= 78.0:
                    result["estimated_state"] = "Karnataka"
                    if 12.8 <= latitude <= 13.2 and 77.4 <= longitude <= 77.8:
                        result["estimated_city"] = "Bengaluru"
                    break
        except:
            pass

        return result
