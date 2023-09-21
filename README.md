# ISOŘ Client
A Scraper for Current Locomotive Positions in the Czech Republic

![Developer Preview](https://github.com/MikolasFromm/IsorClient/blob/main/pic/IsorClient-mainTable-preview.png)

## Introduction
The following web application is a simplified user interface for accessing data from ISOŘ - the railway administrator portal for tracking locomotives and trains. The program scrapes responses from their portal and presents them in a more compressed and better looking HTML table.
**A legitimate ISOŘ account is required to run the application successfully**, and there is no *"demo"* account included in this repository.

## Functionality
This program offers three main functionalities:
- Displaying the current position of a requested locomotive.
- Showing the current route of a requested train.
- Generating an overview table with pre-saved locomotives.

The app maintains its own *locoList* in which users can save their locomotives. This list is also the source of locomotives that are later updated in the main table.

Additionally, the app is capable of displaying ***paintings*** of the locomotives. To *color* a locomotive number in the output table (and the locoRequest response), the following steps are needed:
- Create your own color class in `./data/laky.css`.
- Add a locomotive number to `./data/lokomotivy.json` along with the corresponding CSS class name.

A simple example is provided in [./data/laky.css](https://github.com/MikolasFromm/IsorClient/blob/main/data/laky.css) and [./data/lokomotivy.json](https://github.com/MikolasFromm/IsorClient/blob/main/data/lokomotivy.json).

## Limitations
Since the application does not use an official API endpoint, it is recommended to adhere to the following preset delays in the program:
- Generate the main table once every 30 minutes.
- Make a single request query once every 10 seconds.

While these time limits can be adjusted by the user, it is highly discouraged.

## Developer Note
This program was created to provide an overview of a locomotive fleet for Czech train operators. It was not intended to cause any harm to the railway administrator.
If you encounter any issues or have questions, please feel free to use the local [Issues section](https://github.com/MikolasFromm/IsorClient/issues).
