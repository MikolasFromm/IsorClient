# IsorClient
Scrapper of current locomotive positions in Czech Republic.

![Developer preview](https://github.com/MikolasFromm/IsorClient/blob/main/pic/IsorClient-table-preview.png)

## Introduction
The following WebApp is a simplification of a user overview of data from ISOŘ - railway administrator portal for tracking locomotives and trains. The program scrappes the responses from their portal and prints them out in more compressed, better looking HTML table.
**A legit ISOŘ account is required to run the application successfully** and there is no *"demo"* account included in this repo.

## Functionality
There are three main functionalities this program is capable of:
- Printing current position of a requested locomotive,
- printing current route of a requested train,
- generating an overview table with pre-saved locomotives.

The app has its own *locoList* in which user can save his locomotives. This list is also a source of locomotives that are later updated in the main table.

Secondly the app is capable of showing ***painting*** of the locomotives. In order to *color* a locomotive number in the output table (and the locoRequest resp.), the following is needed:
- creating own color class in ./data/laky.css
- inserting a locoNumber to the ./data/lokomotivy.json with the .css class name.

Very simple example is given in [./data/laky.css](https://github.com/MikolasFromm/IsorClient/blob/main/data/laky.css) and [./data/lokomotivy.json](https://github.com/MikolasFromm/IsorClient/blob/main/data/lokomotivy.json).

## Limitations
Since the application is not using oficial API endpoint, it is recommended to keep the following delays that are preset in the program:
- generation of the main table once in 30min
- single request query once in 10sec

The time limits above can be of course changed by the user, but it is highly not recommended.

## Developer note
This program was made to create an overview of a loco-fleet for any czech train operators. This program was therefore not created to cause any harm to the railway administartor.
In case of any issues or questions, please feel free to use local [Issues section](https://github.com/MikolasFromm/IsorClient/issues).
