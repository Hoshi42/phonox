--
-- PostgreSQL database dump
--

\restrict kFyp9LMChmLWDRnEBEahdghgddKanxJJt2edij0Zhd1eUh2GiN7iXMsREjLKbpC

-- Dumped from database version 15.15 (Debian 15.15-1.pgdg13+1)
-- Dumped by pg_dump version 15.15 (Debian 15.15-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: vinyl_images; Type: TABLE; Schema: public; Owner: phonox
--

CREATE TABLE public.vinyl_images (
    id character varying(36) NOT NULL,
    record_id character varying(36) NOT NULL,
    filename character varying(255) NOT NULL,
    content_type character varying(100) NOT NULL,
    file_size integer NOT NULL,
    file_path character varying(500) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    is_primary boolean NOT NULL
);


ALTER TABLE public.vinyl_images OWNER TO phonox;

--
-- Name: vinyl_records; Type: TABLE; Schema: public; Owner: phonox
--

CREATE TABLE public.vinyl_records (
    id character varying(36) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    artist character varying(255),
    title character varying(255),
    year integer,
    label character varying(255),
    spotify_url character varying(500),
    catalog_number character varying(50),
    barcode character varying(20),
    genres text,
    status character varying(50) NOT NULL,
    validation_passed boolean,
    image_features_extracted boolean,
    confidence double precision NOT NULL,
    auto_commit boolean NOT NULL,
    needs_review boolean NOT NULL,
    evidence_chain text,
    error text,
    user_notes text,
    in_register boolean NOT NULL,
    estimated_value_eur double precision,
    condition character varying(50),
    user_tag character varying(50)
);


ALTER TABLE public.vinyl_records OWNER TO phonox;

--
-- Data for Name: vinyl_images; Type: TABLE DATA; Schema: public; Owner: phonox
--

COPY public.vinyl_images (id, record_id, filename, content_type, file_size, file_path, created_at, is_primary) FROM stdin;
a832483e-bbe5-4058-ae7f-0ca7cc15b3d9	bf4d35d5-44ac-49b0-a8ae-bb8706a8ebb5	R-376907-1622750649-5281.jpg	image/jpeg	99659	/app/uploads/ee600937-e6c3-4a77-ba44-a6aa6c011fa7.jpg	2026-01-25 21:06:00.973092	t
801611d0-87f0-4fc0-9b59-59023b0902be	bf4d35d5-44ac-49b0-a8ae-bb8706a8ebb5	R-376907-1622750593-1566.jpg	image/jpeg	133102	/app/uploads/6ff37966-ffdc-497e-85f5-0ca0519f4e91.jpg	2026-01-25 21:06:00.973104	t
3343f0f6-7648-43b2-9c42-09bc0d8d3d93	bf4d35d5-44ac-49b0-a8ae-bb8706a8ebb5	R-376907-1622750570-9909.jpg	image/jpeg	68020	/app/uploads/69641255-2169-4c0f-b5c9-9c6dc6260216.jpg	2026-01-25 21:06:00.973111	t
74df1b35-d17d-4c0c-a813-e3fa3b02f89d	bf4d35d5-44ac-49b0-a8ae-bb8706a8ebb5	R-367959-1348021211-7343.jpg	image/jpeg	102228	/app/uploads/91858249-892e-402e-8c64-60716002cfe0.jpg	2026-01-25 21:06:00.973117	t
7326b5b8-56f3-440e-a4df-74f771dd7083	ea478751-7843-4eb4-b1b1-579e9f6348a5	s-l140.webp	image/webp	7006	/app/uploads/cbc3343e-74ba-42c9-acee-1dd1c0de8e73.webp	2026-01-25 21:36:21.93458	t
6e88ff8a-2993-467b-8137-12f4452c15ea	ea478751-7843-4eb4-b1b1-579e9f6348a5	WIN_20260125_22_13_49_Pro.jpg	image/jpeg	119482	/app/uploads/6163b117-8fd8-459c-8379-e01c41a6abc5.jpg	2026-01-25 21:36:21.934586	t
6fb9766e-fc3e-403e-80a3-579ebc415b49	ea478751-7843-4eb4-b1b1-579e9f6348a5	WIN_20260125_22_13_30_Pro.jpg	image/jpeg	125814	/app/uploads/3544d57a-72f8-42de-b7c7-88fa467c9cbc.jpg	2026-01-25 21:36:21.934589	t
\.


--
-- Data for Name: vinyl_records; Type: TABLE DATA; Schema: public; Owner: phonox
--

COPY public.vinyl_records (id, created_at, updated_at, artist, title, year, label, spotify_url, catalog_number, barcode, genres, status, validation_passed, image_features_extracted, confidence, auto_commit, needs_review, evidence_chain, error, user_notes, in_register, estimated_value_eur, condition, user_tag) FROM stdin;
88afb865-503f-4921-a511-9b0b505d9bf1	2026-01-25 20:54:21.519472	2026-01-25 20:54:31.065075	Danzig	Danzig	1988	Def American	\N	DEF 24208	\N	["Heavy Metal", "Hard Rock"]	complete	t	f	0.95	t	f	[{"source": "vision", "data": {"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 2, "image_path": "R-376907-1622750593-1566.jpg", "all_barcodes": [], "all_catalog_numbers": ["DEF 24208"], "processed_images": 3, "image_results": [{"artist": "Danzig", "title": "Danzig", "year": null, "label": "Def American", "catalog_number": null, "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.85, "image_index": 1, "image_path": "R-376907-1622750649-5281.jpg"}, {"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 2, "image_path": "R-376907-1622750593-1566.jpg"}, {"artist": "Danzig", "title": "Danzig", "year": null, "label": null, "catalog_number": null, "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.7, "image_index": 3, "image_path": "R-367959-1348021211-7343.jpg"}]}, "confidence": 0.95, "timestamp": "2026-01-25T20:54:31.020990"}]	\N	\N	f	\N	\N	\N
e0f7d629-1f7f-442d-9bc1-3c20bb826bb7	2026-01-25 20:54:54.457063	2026-01-25 20:54:57.198255	Danzig	Danzig	1988	Def American	\N	DEF 24208	\N	["Heavy Metal", "Hard Rock"]	complete	t	f	0.95	t	f	[{"source": "vision", "data": {"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 1, "image_path": "R-376907-1622750593-1566.jpg", "all_barcodes": [], "all_catalog_numbers": ["DEF 24208"], "processed_images": 1, "image_results": [{"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 1, "image_path": "R-376907-1622750593-1566.jpg"}]}, "confidence": 0.95, "timestamp": "2026-01-25T20:54:57.167555"}]	\N	\N	f	\N	\N	\N
5373470d-9802-48a6-bd80-f5a1ae4d8990	2026-01-25 20:56:25.176227	2026-01-25 20:56:28.554065	Danzig	Danzig	1988	Def American	\N	DEF 24208	\N	["Heavy Metal", "Hard Rock"]	complete	t	f	0.8666666666666667	t	f	[{"source": "vision", "data": {"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 1, "image_path": "R-376907-1622750593-1566.jpg", "all_barcodes": [], "all_catalog_numbers": ["DEF 24208"], "processed_images": 1, "image_results": [{"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 1, "image_path": "R-376907-1622750593-1566.jpg"}]}, "confidence": 0.95, "timestamp": "2026-01-25T20:56:28.467734"}, {"source": "musicbrainz", "confidence": 0.8, "data": {"artist": "Danzig", "title": "Danzig", "year": 2009, "label": "American Recordings", "catalog_number": "88697146452", "genres": []}, "timestamp": "2026-01-25T20:56:28.549041"}]	\N	\N	f	\N	\N	\N
c05cc862-91ac-4606-8328-63aae79069c2	2026-01-25 21:31:02.886052	2026-01-25 21:31:08.775565	Mulatu Astatke & The Heliocentrics	Inspiration Information	\N	Strut Records	https://open.spotify.com/album/0e8Xi1tc1yrvmYCWZMGLSb	STRUT107LP	\N	["Ethiopian Jazz", "Afrobeat", "Jazz", "Funk"]	analyzed	t	f	0.7500000000000001	f	t	[{"source": "vision", "data": {"artist": "Mulatu Astatke & The Heliocentrics", "title": "Inspiration Information", "year": null, "label": "Strut Records", "catalog_number": "STRUT107LP", "barcode": null, "genres": ["Ethiopian Jazz", "Afrobeat", "Jazz", "Funk"], "confidence": 0.75, "image_index": 1, "image_path": "s-l140.webp", "all_barcodes": [], "all_catalog_numbers": ["STRUT107LP"], "processed_images": 1, "image_results": [{"artist": "Mulatu Astatke & The Heliocentrics", "title": "Inspiration Information", "year": null, "label": "Strut Records", "catalog_number": "STRUT107LP", "barcode": null, "genres": ["Ethiopian Jazz", "Afrobeat", "Jazz", "Funk"], "confidence": 0.75, "image_index": 1, "image_path": "s-l140.webp"}], "spotify_url": "https://open.spotify.com/album/0e8Xi1tc1yrvmYCWZMGLSb"}, "confidence": 0.75, "timestamp": "2026-01-25T21:31:06.368977"}]	\N	\N	f	\N	\N	\N
53d0ae03-9aff-4b01-8924-4b1b0d7dc308	2026-01-25 20:59:33.950861	2026-01-25 21:04:25.561083	Danzig	Danzig	1988	Def American	\N	DEF 24208	\N	["Heavy Metal", "Hard Rock"]	complete	t	f	0.8666666666666667	t	f	[{"source": "vision", "data": {"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 1, "image_path": "R-376907-1622750593-1566.jpg", "all_barcodes": ["075596075213"], "all_catalog_numbers": ["7559-60752-1", "DEF 24208"], "processed_images": 3, "image_results": [{"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 1, "image_path": "R-376907-1622750593-1566.jpg"}, {"artist": "The Stooges", "title": "The Stooges", "year": null, "label": "Elektra", "catalog_number": "7559-60752-1", "barcode": "075596075213", "genres": ["Rock", "Proto-Punk", "Garage Rock"], "confidence": 0.92, "image_index": 2, "image_path": "R-376907-1622750570-9909.jpg"}, {"artist": "Danzig", "title": "Danzig", "year": null, "label": null, "catalog_number": null, "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.7, "image_index": 3, "image_path": "R-367959-1348021211-7343.jpg"}]}, "confidence": 0.95, "timestamp": "2026-01-25T21:04:25.500354"}, {"source": "musicbrainz", "confidence": 0.8, "data": {"artist": "Danzig", "title": "Danzig", "year": 2009, "label": "American Recordings", "catalog_number": "88697146452", "genres": []}, "timestamp": "2026-01-25T21:04:25.556463"}]	\N	\N	f	\N	\N	\N
bf4d35d5-44ac-49b0-a8ae-bb8706a8ebb5	2026-01-25 21:04:44.150834	2026-01-25 21:16:27.447431	Danzig	Danzig	1988	Def American	https://open.spotify.com/intl-de/album/3elIDlrTtrgKfbxYVgp3uW?si=52D6pxF0SAimO9Wefqk1DQ	DEF 24208	\N	["Heavy Metal", "Hard Rock"]	complete	t	f	1	t	f	[{"source": "vision", "data": {"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 2, "image_path": "R-376907-1622750593-1566.jpg", "all_barcodes": ["5414165042495"], "all_catalog_numbers": ["V 23422-33 025 -1", "DEF 24208"], "processed_images": 4, "image_results": [{"artist": "Danzig", "title": "Danzig", "year": null, "label": "Def American", "catalog_number": null, "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.75, "image_index": 1, "image_path": "R-376907-1622750649-5281.jpg"}, {"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.95, "image_index": 2, "image_path": "R-376907-1622750593-1566.jpg"}, {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "V 23422-33 025 -1", "barcode": "5414165042495", "genres": ["Experimental", "Noise", "Industrial"], "confidence": 0.65, "image_index": 3, "image_path": "R-376907-1622750570-9909.jpg"}, {"artist": "Danzig", "title": "Danzig", "year": null, "label": null, "catalog_number": null, "barcode": null, "genres": ["Heavy Metal", "Hard Rock"], "confidence": 0.7, "image_index": 4, "image_path": "R-367959-1348021211-7343.jpg"}]}, "confidence": 0.95, "timestamp": "2026-01-25T21:04:57.883495"}]	\N	Condition: Mint (M) - Updated 25.1.2026	t	220	Mint (M)	Jan
1fdc1417-8d7d-40e0-b1ac-8c6b9253a5eb	2026-01-25 21:16:34.870003	2026-01-25 21:16:44.244999	\N	\N	\N	\N	\N	BLCKND055-1	6024550124011	\N	complete	t	f	0.7500000000000001	f	t	[{"source": "vision", "data": {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 2, "image_path": "WIN_20260125_22_13_49_Pro.jpg", "all_barcodes": ["6024550124011"], "all_catalog_numbers": ["BLCKND055-1"], "processed_images": 3, "image_results": [{"artist": "Orchestral Manoeuvres in the Dark", "title": "Dazzle Ships", "year": null, "label": null, "catalog_number": null, "barcode": null, "genres": ["Synth-pop", "New Wave", "Electronic"], "confidence": 0.4, "image_index": 1, "image_path": "s-l140.webp"}, {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 2, "image_path": "WIN_20260125_22_13_49_Pro.jpg"}, {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": null, "genres": ["Heavy Metal", "Thrash Metal"], "confidence": 0.75, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg"}]}, "confidence": 0.75, "timestamp": "2026-01-25T21:16:44.238975"}]	\N	\N	f	\N	\N	\N
d9230b65-6941-4663-ab7d-47f9033d7b66	2026-01-25 21:19:36.372443	2026-01-25 21:19:47.030562	Metallica	72 Seasons	\N	\N	https://open.spotify.com/album/6UwjRSX9RQyNgJ3LwYhr9i	\N	858034001244	["Heavy Metal", "Thrash Metal", "Hard Rock"]	complete	t	f	0.8533333333333333	t	f	[{"source": "vision", "data": {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "858034001244", "genres": ["Heavy Metal", "Thrash Metal", "Hard Rock"], "confidence": 0.92, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg", "all_barcodes": ["6024550124011", "858034001244"], "all_catalog_numbers": ["BLCKND055-1"], "processed_images": 3, "image_results": [{"artist": "Violent Femmes", "title": "Hallowed Ground", "year": null, "label": "Slash Records", "catalog_number": null, "barcode": null, "genres": ["Alternative Rock", "Folk Punk"], "confidence": 0.65, "image_index": 1, "image_path": "s-l140.webp"}, {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 2, "image_path": "WIN_20260125_22_13_49_Pro.jpg"}, {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "858034001244", "genres": ["Heavy Metal", "Thrash Metal", "Hard Rock"], "confidence": 0.92, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg"}], "spotify_url": "https://open.spotify.com/album/6UwjRSX9RQyNgJ3LwYhr9i"}, "confidence": 0.92, "timestamp": "2026-01-25T21:19:45.433719"}, {"source": "musicbrainz", "confidence": 0.8, "data": {"artist": "Metallica", "title": "72 Seasons", "year": 2023, "label": "Blackened", "catalog_number": null, "genres": []}, "timestamp": "2026-01-25T21:19:45.586371"}]	\N	\N	f	\N	\N	\N
8b986b05-6c86-45ea-b9ff-fbca0ec2827f	2026-01-25 21:20:34.912526	2026-01-25 21:20:44.891195	Metallica	72 Seasons	\N	\N	https://open.spotify.com/album/6UwjRSX9RQyNgJ3LwYhr9i	\N	858005012409	["Heavy Metal", "Thrash Metal", "Hard Rock"]	complete	t	f	0.8533333333333333	t	f	[{"source": "vision", "data": {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "858005012409", "genres": ["Heavy Metal", "Thrash Metal", "Hard Rock"], "confidence": 0.92, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg", "all_barcodes": ["858005012409", "6024550124011"], "all_catalog_numbers": ["BLCKND055-1"], "processed_images": 3, "image_results": [{"artist": "Vanilla Ice", "title": "To The Extreme", "year": null, "label": null, "catalog_number": null, "barcode": null, "genres": ["Hip Hop", "Pop Rap"], "confidence": 0.4, "image_index": 1, "image_path": "s-l140.webp"}, {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 2, "image_path": "WIN_20260125_22_13_49_Pro.jpg"}, {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "858005012409", "genres": ["Heavy Metal", "Thrash Metal", "Hard Rock"], "confidence": 0.92, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg"}], "spotify_url": "https://open.spotify.com/album/6UwjRSX9RQyNgJ3LwYhr9i"}, "confidence": 0.92, "timestamp": "2026-01-25T21:20:44.289282"}, {"source": "musicbrainz", "confidence": 0.8, "data": {"artist": "Metallica", "title": "72 Seasons", "year": 2023, "label": "Blackened", "catalog_number": null, "genres": []}, "timestamp": "2026-01-25T21:20:44.358939"}]	\N	\N	f	\N	\N	\N
ec4f72e1-c392-4a11-99df-c0930e9385ed	2026-01-25 21:23:08.767958	2026-01-25 21:23:18.012816	\N	\N	\N	\N	\N	BLCKND055-1	6024550124011	\N	complete	t	f	0.7500000000000001	f	t	[{"source": "vision", "data": {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 2, "image_path": "WIN_20260125_22_13_49_Pro.jpg", "all_barcodes": ["6024550124011", "075021234567"], "all_catalog_numbers": ["BLCKND055-1"], "processed_images": 3, "image_results": [{"artist": "Primal Scream", "title": "Screamadelica", "year": null, "label": "Creation Records", "catalog_number": null, "barcode": null, "genres": ["Alternative Rock", "Electronic", "Dance"], "confidence": 0.45, "image_index": 1, "image_path": "s-l140.webp"}, {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 2, "image_path": "WIN_20260125_22_13_49_Pro.jpg"}, {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "075021234567", "genres": ["Heavy Metal", "Thrash Metal", "Hard Rock"], "confidence": 0.75, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg"}]}, "confidence": 0.75, "timestamp": "2026-01-25T21:23:18.007678"}]	\N	\N	f	\N	\N	\N
8a66733c-3728-46e7-ae7b-d7bdb887f86b	2026-01-25 21:28:28.318538	2026-01-25 21:28:39.252246	Metallica	72 Seasons	\N	\N	https://open.spotify.com/album/6UwjRSX9RQyNgJ3LwYhr9i	\N	888072456891	["Heavy Metal", "Thrash Metal"]	analyzed	t	f	0.8533333333333333	t	f	[{"source": "vision", "data": {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "888072456891", "genres": ["Heavy Metal", "Thrash Metal"], "confidence": 0.92, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg", "all_barcodes": ["888072456891", "6024550124011"], "all_catalog_numbers": ["BLCKND055-1"], "processed_images": 3, "image_results": [{"artist": "Maserati", "title": "Maserati VII", "year": null, "label": "Temporary Residence Limited", "catalog_number": null, "barcode": null, "genres": ["Post-Rock", "Electronic", "Instrumental"], "confidence": 0.65, "image_index": 1, "image_path": "s-l140.webp"}, {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 2, "image_path": "WIN_20260125_22_13_49_Pro.jpg"}, {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "888072456891", "genres": ["Heavy Metal", "Thrash Metal"], "confidence": 0.92, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg"}], "spotify_url": "https://open.spotify.com/album/6UwjRSX9RQyNgJ3LwYhr9i"}, "confidence": 0.92, "timestamp": "2026-01-25T21:28:38.808038"}, {"source": "musicbrainz", "confidence": 0.8, "data": {"artist": "Metallica", "title": "72 Seasons", "year": 2023, "label": "Blackened", "catalog_number": null, "genres": []}, "timestamp": "2026-01-25T21:28:38.891640"}]	\N	\N	f	\N	\N	\N
a3330e1a-c48c-43cf-bb84-65a3c3d2170d	2026-01-25 21:34:22.071479	2026-01-25 21:35:21.981653	\N	\N	\N	\N	\N	BLCKND055-1	6024550124011	["Heavy Metal", "Thrash Metal"]	complete	t	f	0.7500000000000001	f	t	[{"source": "vision", "data": {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 1, "image_path": "WIN_20260125_22_13_49_Pro.jpg", "all_barcodes": ["6024550124011"], "all_catalog_numbers": ["BLCKND055-1"], "processed_images": 1, "image_results": [{"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 1, "image_path": "WIN_20260125_22_13_49_Pro.jpg"}]}, "confidence": 0.75, "timestamp": "2026-01-25T21:35:21.975200"}]	\N	\N	f	\N	\N	\N
ea478751-7843-4eb4-b1b1-579e9f6348a5	2026-01-25 21:35:45.718692	2026-01-25 21:54:55.661298	Metallica	72 Seasons	\N	\N	https://open.spotify.com/album/6UwjRSX9RQyNgJ3LwYhr9i	\N	888072456174	["Heavy Metal", "Thrash Metal", "Hard Rock"]	analyzed	t	f	1	t	f	[{"source": "vision", "data": {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "888072456174", "genres": ["Heavy Metal", "Thrash Metal", "Hard Rock"], "confidence": 0.92, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg", "all_barcodes": ["6024550124011", "888072456174"], "all_catalog_numbers": ["BLCKND055-1"], "processed_images": 3, "image_results": [{"artist": "Orchestral Manoeuvres in the Dark", "title": "Dazzle Ships", "year": null, "label": null, "catalog_number": null, "barcode": null, "genres": ["Electronic", "Synthpop", "New Wave"], "confidence": 0.45, "image_index": 1, "image_path": "s-l140.webp"}, {"artist": null, "title": null, "year": null, "label": null, "catalog_number": "BLCKND055-1", "barcode": "6024550124011", "genres": [], "confidence": 0.75, "image_index": 2, "image_path": "WIN_20260125_22_13_49_Pro.jpg"}, {"artist": "Metallica", "title": "72 Seasons", "year": null, "label": null, "catalog_number": null, "barcode": "888072456174", "genres": ["Heavy Metal", "Thrash Metal", "Hard Rock"], "confidence": 0.92, "image_index": 3, "image_path": "WIN_20260125_22_13_30_Pro.jpg"}], "spotify_url": "https://open.spotify.com/album/6UwjRSX9RQyNgJ3LwYhr9i"}, "confidence": 0.92, "timestamp": "2026-01-25T21:35:55.052576"}, {"source": "musicbrainz", "confidence": 0.8, "data": {"artist": "Metallica", "title": "72 Seasons", "year": 2023, "label": "Blackened", "catalog_number": null, "genres": []}, "timestamp": "2026-01-25T21:35:55.111939"}]	\N	Condition: Mint (M) - Updated 25.1.2026	t	23	Mint (M)	Jan
\.


--
-- Name: vinyl_images vinyl_images_pkey; Type: CONSTRAINT; Schema: public; Owner: phonox
--

ALTER TABLE ONLY public.vinyl_images
    ADD CONSTRAINT vinyl_images_pkey PRIMARY KEY (id);


--
-- Name: vinyl_records vinyl_records_pkey; Type: CONSTRAINT; Schema: public; Owner: phonox
--

ALTER TABLE ONLY public.vinyl_records
    ADD CONSTRAINT vinyl_records_pkey PRIMARY KEY (id);


--
-- Name: ix_vinyl_images_id; Type: INDEX; Schema: public; Owner: phonox
--

CREATE INDEX ix_vinyl_images_id ON public.vinyl_images USING btree (id);


--
-- Name: ix_vinyl_records_id; Type: INDEX; Schema: public; Owner: phonox
--

CREATE INDEX ix_vinyl_records_id ON public.vinyl_records USING btree (id);


--
-- Name: ix_vinyl_records_status; Type: INDEX; Schema: public; Owner: phonox
--

CREATE INDEX ix_vinyl_records_status ON public.vinyl_records USING btree (status);


--
-- Name: ix_vinyl_records_user_tag; Type: INDEX; Schema: public; Owner: phonox
--

CREATE INDEX ix_vinyl_records_user_tag ON public.vinyl_records USING btree (user_tag);


--
-- Name: vinyl_images vinyl_images_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: phonox
--

ALTER TABLE ONLY public.vinyl_images
    ADD CONSTRAINT vinyl_images_record_id_fkey FOREIGN KEY (record_id) REFERENCES public.vinyl_records(id);


--
-- PostgreSQL database dump complete
--

\unrestrict kFyp9LMChmLWDRnEBEahdghgddKanxJJt2edij0Zhd1eUh2GiN7iXMsREjLKbpC

