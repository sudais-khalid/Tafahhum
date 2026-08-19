-- 009_ocr_empty_guard.sql — an empty OCR result must not lock a page
--
-- 008 froze ocr_raw_text as soon as it was non-NULL. An engine that fails and
-- returns an empty string therefore locked the page permanently: the failure was
-- treated as a reading worth preserving, and re-running a better engine on that
-- page became impossible without disabling the trigger.
--
-- The immutability guarantee should protect *text that was actually read*. An
-- empty result is the absence of a reading, not a reading.

CREATE OR REPLACE FUNCTION protect_ocr_raw_text() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    IF OLD.ocr_raw_text IS NOT NULL
       AND length(trim(OLD.ocr_raw_text)) > 0
       AND NEW.ocr_raw_text IS DISTINCT FROM OLD.ocr_raw_text THEN
        RAISE EXCEPTION
            'scan_page.ocr_raw_text is immutable once written (page %). Write to ocr_verified_text.',
            OLD.id;
    END IF;
    RETURN NEW;
END;
$fn$;

-- Clear the empty rows 008 wrote, so those pages can be read again.
UPDATE scan_page
SET ocr_raw_text = NULL, ocr_normalized_text = NULL
WHERE ocr_raw_text IS NOT NULL AND length(trim(ocr_raw_text)) = 0;
