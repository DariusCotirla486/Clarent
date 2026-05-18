package com.clarent.service;

import com.clarent.domain.team.TeamDocument;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.hwpf.HWPFDocument;
import org.apache.poi.hwpf.extractor.WordExtractor;
import org.apache.poi.xwpf.extractor.XWPFWordExtractor;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
public class TeamDocumentTextExtractor {
    public String extract(TeamDocument document) {
        try {
            return switch (extension(document.getFileName())) {
                case "txt" -> extractText(document.getData());
                case "pdf" -> extractPdf(document.getData());
                case "docx" -> extractDocx(document.getData());
                case "doc" -> extractDoc(document.getData());
                default -> throw new ResponseStatusException(
                        HttpStatus.BAD_REQUEST,
                        "Unsupported team context document type"
                );
            };
        } catch (IOException exception) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Could not read the uploaded team context document"
            );
        }
    }

    private String extractText(byte[] data) {
        String text = new String(data, StandardCharsets.UTF_8);
        if (text.indexOf('\uFFFD') >= 0) {
            text = new String(data, Charset.forName("windows-1252"));
        }
        return stripBom(text);
    }

    private String extractPdf(byte[] data) throws IOException {
        try (PDDocument document = Loader.loadPDF(data)) {
            return new PDFTextStripper().getText(document);
        }
    }

    private String extractDocx(byte[] data) throws IOException {
        try (
                XWPFDocument document = new XWPFDocument(new ByteArrayInputStream(data));
                XWPFWordExtractor extractor = new XWPFWordExtractor(document)
        ) {
            return extractor.getText();
        }
    }

    private String extractDoc(byte[] data) throws IOException {
        try (
                HWPFDocument document = new HWPFDocument(new ByteArrayInputStream(data));
                WordExtractor extractor = new WordExtractor(document)
        ) {
            return extractor.getText();
        }
    }

    private String extension(String fileName) {
        int dotIndex = fileName.lastIndexOf('.');
        if (dotIndex < 0 || dotIndex == fileName.length() - 1) {
            return "";
        }
        return fileName.substring(dotIndex + 1).toLowerCase(Locale.ROOT);
    }

    private String stripBom(String text) {
        if (!text.isEmpty() && text.charAt(0) == '\uFEFF') {
            return text.substring(1);
        }
        return text;
    }
}
