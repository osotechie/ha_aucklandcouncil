<div align="center">

<img src="https://avatars.githubusercontent.com/u/34251619?v=4" align="center" width="144px" height="144px"/>

### Home Assistant - Custom Integration - Auckland Council

</div>

---

## 📖 Overview

This is a HACS integration for Auckland Council, helping you track rubbish, recycling, and food scrap collection dates from the Auckland Council website. Now you will know exactly when your recycling will be collected. Or know when collection dates have changed due to things like public holidays.

Using this integration you could easily build automations to help remind you to put the rubbish the night before. Never forget to put your rubbish out on the right night again.

## 💽 Installation

### HACS Based Install

If you are using HACS to manage custom components in your Home Assistant installation you can easily add this repo as a custom repo in HACS using the My button.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=ha_aucklandcouncil&category=Integration&owner=OSoTechie)

  1. Confirm you wish to add the repo
  2. Click download to install the repo
  3. Restart Home Assistant
  
### Manual Install

  1. Create custom_components folder if it does not exist to get following structure\
     `config/custom_components`

  2. Create `aucklandcouncil` folder inside the **custom_components** folder
     `config/custom_components/aucklandcouncil`

  3. Download a copy of this repo, and copy all files from [custom_components/aucklandcouncil/](custom_components/aucklandcouncil/) into the previously created folder
  
  4. Restart Home Assistant 

<br>

## 🗒️Configuration

Once installed you can use the following My button to setup the integration in your to Home Assistant deployment.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=aucklandcouncil)

### Finding Your Property ID

1. Go to [Auckland Council Collection Days](https://www.aucklandcouncil.govt.nz/en/rubbish-recycling/rubbish-recycling-collections/rubbish-recycling-collection-days.html)
2. Enter your address
3. The Property ID will be the Assessment Number (e.g. 12344153300)

<br>

## 🔧 Troubleshooting

For issues or feature requests, please check the Home Assistant logs first. The integration logs detailed information about data parsing and any errors encountered.

### Sensors show "Unknown"
- Check that your Property ID is correct
- Verify the Auckland Council website is accessible
- Check Home Assistant logs for errors

### Integration not appearing
- Ensure the folder is in the correct location: `/config/custom_components/auckland_council/`
- Restart Home Assistant after installation
- Check that all required files are present

## 🙌 Acknowledgements

The source code for this integration was largly created using [GitHub Copilot](https://github.com/copilot).
