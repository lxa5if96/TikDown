// ============================================================
// ELEMENTS
// ============================================================

const downloadButton =
    document.getElementById("download-btn");

const urlInput =
    document.getElementById("video-url");

const errorElement =
    document.getElementById("error");

const result =
    document.getElementById("result");

const videoButton =
    document.getElementById("video-btn");

const hdButton =
    document.getElementById("hd-btn");

const musicButton =
    document.getElementById("music-btn");

const themeToggle =
    document.getElementById("theme-toggle");


// ============================================================
// PLATFORM DETECTION
// ============================================================

function detectPlatform(url) {

    try {

        const parsed = new URL(url);

        const host =
            parsed.hostname.toLowerCase();


        // Instagram
        if (
            host === "instagram.com" ||
            host === "www.instagram.com"
        ) {
            return "instagram";
        }


        // TikTok
        if (
            host === "tiktok.com" ||
            host === "www.tiktok.com" ||
            host === "m.tiktok.com" ||
            host === "vm.tiktok.com" ||
            host === "vt.tiktok.com" ||
            host.endsWith(".tiktok.com")
        ) {
            return "tiktok";
        }


        return null;

    } catch {

        return null;
    }
}


// ============================================================
// MAIN DOWNLOAD / PROCESS BUTTON
// ============================================================

downloadButton.addEventListener(
    "click",
    async () => {

        const url =
            urlInput.value.trim();


        // Clear previous error
        errorElement.textContent = "";


        // Hide previous result
        result.classList.add("hidden");


        // ----------------------------------------------------
        // Empty URL
        // ----------------------------------------------------

        if (!url) {

            errorElement.textContent =
                "Please paste a TikTok or Instagram URL.";

            return;
        }


        // ----------------------------------------------------
        // Detect platform
        // ----------------------------------------------------

        const platform =
            detectPlatform(url);


        if (!platform) {

            errorElement.textContent =
                "Please enter a valid TikTok or Instagram URL.";

            return;
        }


        // ----------------------------------------------------
        // Loading
        // ----------------------------------------------------

        downloadButton.textContent =
            `Processing ${platform}...`;

        downloadButton.disabled =
            true;


        try {

            // =================================================
            // SELECT BACKEND ENDPOINT
            // =================================================

            const endpoint =
                platform === "instagram"
                    ? "/api/instagram/download"
                    : "/api/download";


            // =================================================
            // SEND REQUEST
            // =================================================

            const response =
                await fetch(
                    endpoint,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({
                            url: url
                        })
                    }
                );


            // =================================================
            // HANDLE ERROR
            // =================================================

            if (!response.ok) {

                let message =
                    `Unable to process ${platform} URL.`;

                try {

                    const errorData =
                        await response.json();

                    if (errorData.detail) {
                        message =
                            errorData.detail;
                    }

                } catch {
                    // Ignore JSON parsing error
                }

                throw new Error(message);
            }


            // =================================================
            // PARSE RESPONSE
            // =================================================

            const data =
                await response.json();


            console.log(
                `${platform} API response:`,
                data
            );


            // =================================================
            // INSTAGRAM
            // =================================================

            if (platform === "instagram") {

                const cover =
                    document.getElementById("cover");

                const title =
                    document.getElementById("title");

                const author =
                    document.getElementById("author");

                const duration =
                    document.getElementById("duration");


                // Thumbnail
                if (data.thumbnail) {

                    cover.src =
                        data.thumbnail;

                    cover.style.display =
                        "block";

                } else {

                    cover.removeAttribute("src");

                    cover.style.display =
                        "none";
                }


                // Title
                title.textContent =
                    "Instagram Video";


                // Author
                author.textContent =
                    data.author
                        ? "@" + data.author
                        : "";


                // Duration
                duration.textContent =
                    data.duration || "0";


                // Instagram only needs one download button
                videoButton.style.display =
                    "inline-block";

                videoButton.textContent =
                    "Download Instagram Video";

                videoButton.onclick = () => {

                    startDownload(
                        data.download_url
                    );
                };


                // Hide TikTok-specific buttons
                hdButton.style.display =
                    "none";

                musicButton.style.display =
                    "none";


                // Show result
                result.classList.remove(
                    "hidden"
                );


                return;
            }


            // =================================================
            // TIKTOK
            // =================================================

            const cover =
                document.getElementById("cover");

            const title =
                document.getElementById("title");

            const author =
                document.getElementById("author");

            const duration =
                document.getElementById("duration");


            // Cover
            if (data.cover) {

                cover.src =
                    data.cover;

                cover.style.display =
                    "block";

            } else {

                cover.removeAttribute("src");

                cover.style.display =
                    "none";
            }


            // Title
            title.textContent =
                data.title ||
                "TikTok Video";


            // Author
            author.textContent =
                "@" +
                (
                    data.author?.username ||
                    "unknown"
                );


            // Duration
            duration.textContent =
                data.duration || 0;


            const downloads =
                data.downloads || {};


            // ------------------------------------------------
            // Normal video
            // ------------------------------------------------

            if (downloads.video) {

                videoButton.style.display =
                    "inline-block";

                videoButton.textContent =
                    "Download Video";

                videoButton.onclick = () => {

                    startDownload(
                        downloads.video
                    );
                };

            } else {

                videoButton.style.display =
                    "none";
            }


            // ------------------------------------------------
            // HD video
            // ------------------------------------------------

            if (downloads.hd_video) {

                hdButton.style.display =
                    "inline-block";

                hdButton.textContent =
                    "Download HD";

                hdButton.onclick = () => {

                    startDownload(
                        downloads.hd_video
                    );
                };

            } else {

                hdButton.style.display =
                    "none";
            }


            // ------------------------------------------------
            // Audio
            // ------------------------------------------------

            if (downloads.music) {

                musicButton.style.display =
                    "inline-block";

                musicButton.textContent =
                    "Download Audio";

                musicButton.onclick = () => {

                    startDownload(
                        downloads.music
                    );
                };

            } else {

                musicButton.style.display =
                    "none";
            }


            // ------------------------------------------------
            // Show result
            // ------------------------------------------------

            result.classList.remove(
                "hidden"
            );

        } catch (error) {

            console.error(
                "Download processing error:",
                error
            );

            errorElement.textContent =
                error.message ||
                "Something went wrong.";

            result.classList.add(
                "hidden"
            );

        } finally {

            downloadButton.textContent =
                "Download";

            downloadButton.disabled =
                false;
        }
    }
);


// ============================================================
// START FILE DOWNLOAD
// ============================================================

function startDownload(downloadPath) {

    if (!downloadPath) {

        errorElement.textContent =
            "Download link is unavailable.";

        return;
    }


    const downloadUrl =
        new URL(
            downloadPath,
            window.location.origin
        ).href;


    console.log(
        "Starting download:",
        downloadUrl
    );


    window.location.href =
        downloadUrl;
}


// ============================================================
// DARK MODE
// ============================================================

const savedTheme =
    localStorage.getItem("theme");


if (savedTheme === "dark") {

    document.body.classList.add(
        "dark"
    );

    themeToggle.textContent =
        "☀️";

} else {

    themeToggle.textContent =
        "🌙";
}


themeToggle.addEventListener(
    "click",
    () => {

        document.body.classList.toggle(
            "dark"
        );


        const isDark =
            document.body.classList.contains(
                "dark"
            );


        if (isDark) {

            themeToggle.textContent =
                "☀️";

            localStorage.setItem(
                "theme",
                "dark"
            );

        } else {

            themeToggle.textContent =
                "🌙";

            localStorage.setItem(
                "theme",
                "light"
            );
        }
    }
);