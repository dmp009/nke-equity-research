"""Business facts quoted from Nike's FY2026 Form 10-K (fiscal year ended 31 May 2026).

Source file: data/raw/10k/nke-20260531.htm (Item 1 Business and Item 7 MD&A). USD millions.
"""

SOURCE = "Nike FY2026 Form 10-K (filed July 2026), Items 1 and 7"

REVENUE_BY_SEGMENT = {  # FY2026, FY2025, FY2024
    "North America": (20511, 19572, 21396),
    "EMEA": (12572, 12257, 13607),
    "Greater China": (5847, 6586, 7545),
    "Asia Pacific & Latin America": (6243, 6251, 6729),
    "Converse": (1174, 1692, 2082),
}
EBIT_BY_SEGMENT = {  # FY2026, FY2025, FY2024
    "North America": (5376, 4735, 5822),
    "EMEA": (2417, 2575, 3388),
    "Greater China": (1278, 1602, 2309),
    "Asia Pacific & Latin America": (1387, 1527, 1885),
    "Converse": (18, 240, 474),
}
NIKE_BRAND_BY_CHANNEL = {  # FY2026, FY2025, FY2024
    "Wholesale": (27453, 25883, 27758),
    "NIKE Direct": (17720, 18783, 21519),
}
NIKE_BRAND_BY_PRODUCT_FY2026 = {"Footwear": 29525, "Apparel": 13449, "Equipment": 2199}
JORDAN_BRAND = (7034, 7270, 8701)  # FY2026, FY2025, FY2024
FOOTWEAR_SOURCING_FY2026 = {"Vietnam": 0.52, "Indonesia": 0.27, "China": 0.16, "Other": 0.05}
APPAREL_SOURCING_FY2026 = {"Vietnam": 0.34, "Cambodia": 0.15, "China": 0.12, "Other": 0.39}
FOOTWEAR_FACTORIES, FOOTWEAR_COUNTRIES, FOOTWEAR_MANUFACTURERS = 95, 11, 15
TOP4_FOOTWEAR_MANUFACTURERS_SHARE = 0.60
US_SHARE_OF_REVENUE_FY2026 = 0.44
TOP3_US_CUSTOMERS_SHARE_OF_US_SALES = 0.29
EMPLOYEES = 73000
IMPORT_DUTY_RECOVERY_RECEIVABLE = 684  # XBRL ReceivableForRecoveryOfImportDutiesNet, 31 May 2026
