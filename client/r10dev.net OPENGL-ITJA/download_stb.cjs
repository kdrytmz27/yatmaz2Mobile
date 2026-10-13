const https = require("https");
const fs = require("fs");

https.get("https://raw.githubusercontent.com/nothings/stb/master/stb_image.h", (res) => {
    let data = [];
    res.on("data", chunk => data.push(chunk));
    res.on("end", () => {
        fs.writeFileSync("clientsource/EterImageLib/stb_image.h", Buffer.concat(data));
        console.log("stb_image.h downloaded successfully!");
    });
});
