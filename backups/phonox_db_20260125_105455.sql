--
-- PostgreSQL database dump
--

\restrict 7Uk0xaJAaIR1Z9qzoHQomeuH6Xr6iZyXE84uGFYxCWfpSLEe85pXaXCHTEYcitZ

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
    condition character varying(50)
);


ALTER TABLE public.vinyl_records OWNER TO phonox;

--
-- Data for Name: vinyl_images; Type: TABLE DATA; Schema: public; Owner: phonox
--

COPY public.vinyl_images (id, record_id, filename, content_type, file_size, file_path, created_at, is_primary) FROM stdin;
e5359cd4-245b-4051-a445-0d40ad4192b2	44e74e9d-a544-4438-8bb3-8a818b628657	R-376907-1622750593-1566.jpg	image/jpeg	133102	/app/uploads/1474de69-1709-472c-b509-80e171866fda.jpg	2026-01-25 09:31:10.743389	t
\.


--
-- Data for Name: vinyl_records; Type: TABLE DATA; Schema: public; Owner: phonox
--

COPY public.vinyl_records (id, created_at, updated_at, artist, title, year, label, spotify_url, catalog_number, genres, status, validation_passed, image_features_extracted, confidence, auto_commit, needs_review, evidence_chain, error, user_notes, in_register, estimated_value_eur, condition) FROM stdin;
44e74e9d-a544-4438-8bb3-8a818b628657	2026-01-25 09:30:43.742922	2026-01-25 09:35:55.850205	Danzig	Danzig	1988	Def American	https://open.spotify.com/intl-de/album/42qvuRV13qTc2LMVI9CqKv	DEF 24208	["Heavy Metal", "Hard Rock", "Blues Rock"]	complete	t	f	1	t	f	[{"source": "vision", "data": {"artist": "Danzig", "title": "Danzig", "year": 1988, "label": "Def American", "catalog_number": "DEF 24208", "genres": ["Heavy Metal", "Hard Rock", "Blues Rock"], "confidence": 0.95}, "confidence": 0.95, "timestamp": "2026-01-25T09:30:46.644513"}, {"source": "musicbrainz", "confidence": 0.8, "data": {"artist": "Danzig", "title": "Danzig", "year": 1989, "label": "Def American Recordings", "catalog_number": "838 487-2", "genres": []}, "timestamp": "2026-01-25T09:30:47.068546"}]	\N	Condition: null - Updated 25.1.2026	t	220	Mint (M)
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
-- Name: vinyl_images vinyl_images_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: phonox
--

ALTER TABLE ONLY public.vinyl_images
    ADD CONSTRAINT vinyl_images_record_id_fkey FOREIGN KEY (record_id) REFERENCES public.vinyl_records(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 7Uk0xaJAaIR1Z9qzoHQomeuH6Xr6iZyXE84uGFYxCWfpSLEe85pXaXCHTEYcitZ

